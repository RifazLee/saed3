from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import spglib
import numpy as np
from typing import Optional

app = FastAPI(title="SAED spglib systematic-absence service", version="1.0.0")

class Reflection(BaseModel):
    h: int
    k: int
    l: int

class AbsenceRequest(BaseModel):
    space_group_number: int = Field(ge=1, le=230)
    space_group_symbol: str
    setting: str = "Standard"
    reflections: list[Reflection]

def phase_sum_is_allowed(rotations, translations, hkl, tol=1e-7):
    h = np.asarray(hkl, dtype=int)
    phases = []
    for rot, trans in zip(rotations, translations):
        # Operations mapping this reciprocal vector onto itself form its little group.
        if np.array_equal(np.asarray(rot, dtype=int).T @ h, h):
            phases.append(np.exp(2j * np.pi * float(np.dot(h, trans))))
    if not phases:
        return True
    return abs(sum(phases)) > tol

@app.get("/health")
def health():
    return {"ok": True, "spglib_version": spglib.__version__}

@app.post("/systematic-absences")
def systematic_absences(req: AbsenceRequest):
    candidates = []
    for hall_number in range(1, 531):
        sg = spglib.get_spacegroup_type(hall_number)
        if sg and sg.number == req.space_group_number:
            candidates.append((hall_number, sg))
    if not candidates:
        raise HTTPException(422, "Space group number not found in spglib database")
    # If caller provides a setting label, prefer matching HM symbol when possible.
    target = req.space_group_symbol.replace(" ", "").lower()
    matches = []
    for hall, sg in candidates:
        hm_short = (sg.international_short or "").replace(" ", "").lower()
        hm_full = (sg.international_full or "").replace(" ", "").lower()
        if target in (hm_short, hm_full):
            matches.append((hall, sg))
    if len(matches) == 1:
        selected = matches[0]
    elif len(matches) > 1:
        setting_key = req.setting.replace(" ", "").lower()
        setting_matches = [
            item for item in matches
            if setting_key in (item[1].hall_symbol or "").replace(" ", "").lower()
            or setting_key == str(item[0])
        ]
        if len(setting_matches) == 1:
            selected = setting_matches[0]
        else:
            raise HTTPException(422, "Ambiguous Hall setting. Supply the exact Hall symbol or Hall number in the Setting field.")
    elif len(candidates) == 1:
        selected = candidates[0]
    else:
        raise HTTPException(422, "Space-group symbol does not uniquely identify a Hall setting. Supply an exact setting.")
    hall, sg = selected
    sym = spglib.get_symmetry_from_database(hall)
    if sym is None:
        raise HTTPException(500, "Could not load symmetry operations")
    out=[]
    for ref in req.reflections:
        allowed=phase_sum_is_allowed(sym["rotations"], sym["translations"], (ref.h,ref.k,ref.l))
        out.append({"h":ref.h,"k":ref.k,"l":ref.l,"allowed":bool(allowed)})
    return {"space_group":{"number":sg.number,"international_short":sg.international_short,
            "international_full":sg.international_full,"hall_number":hall,"hall_symbol":sg.hall_symbol},
            "reflections":out}


# CIF analysis: Gemmi expands asymmetric-unit sites; abTEM provides Lobato
# electron scattering factors f(s), with s^2 in inverse-angstrom squared.
from pydantic import BaseModel, Field
import math
import re

class CifReflection(BaseModel):
    h: int
    k: int
    l: int

class CifAnalyzeRequest(BaseModel):
    cif_text: str = Field(min_length=20, max_length=5_000_000)
    reflections: list[CifReflection] = Field(default_factory=list, max_length=50000)
    f_tolerance: float = Field(default=1e-8, gt=0, le=1e-3)

def _has_cif_tag(block, tag):
    values = list(block.find_values(tag))
    return any(str(v).strip() not in ('', '.', '?') for v in values)

def _cif_float(value):
    if value is None or str(value).strip() in ('', '.', '?'):
        return None
    m = re.fullmatch(r'\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)(?:\(\d+\))?\s*', str(value))
    if not m:
        raise ValueError(f'Invalid CIF numeric value: {value}')
    return float(m.group(1))

def _atom_element(site):
    return site.element.name

def _find_hall_number(spacegroup, hall_symbol):
    if spacegroup is None:
        return None
    target = ''.join(str(hall_symbol or '').split()).lower()
    for hall_no in range(1, 531):
        sg_type = spglib.get_spacegroup_type(hall_no)
        if sg_type and sg_type.number == int(spacegroup.number) and ''.join(sg_type.hall_symbol.split()).lower() == target:
            return hall_no
    # If CIF omits Hall symbol, accept a unique database setting only.
    matches = [n for n in range(1, 531) if (spglib.get_spacegroup_type(n) and spglib.get_spacegroup_type(n).number == int(spacegroup.number))]
    return matches[0] if len(matches) == 1 else None

@app.post('/cif/analyze')
def cif_analyze(req: CifAnalyzeRequest):
    try:
        import gemmi
        doc = gemmi.cif.read_string(req.cif_text)
        if len(doc) == 0:
            raise ValueError('CIF contains no data block')
        block = doc[0]
        small = gemmi.make_small_structure_from_block(block)
        if not small.sites:
            raise ValueError('CIF has no atom-site fractional coordinates')
        expanded = small.get_all_unit_cell_sites()
        # Gemmi's full-cell expansion includes conventional-cell centering translations.
        unique = {}
        for site in expanded:
            xyz = tuple(round(float(v) % 1.0, 8) for v in (site.fract.x, site.fract.y, site.fract.z))
            key = (site.label, _atom_element(site), *xyz)
            unique[key] = {
                'label': site.label, 'element': _atom_element(site),
                'x': xyz[0], 'y': xyz[1], 'z': xyz[2],
                'occupancy': float(site.occ), 'charge': float(site.charge),
            }
        atoms = list(unique.values())
        if not atoms:
            raise ValueError('CIF symmetry expansion produced no atoms')

        # Gemmi initializes missing Uiso to zero. Distinguish absent CIF tags from explicit zero.
        has_u = _has_cif_tag(block, '_atom_site_U_iso_or_equiv')
        has_b = _has_cif_tag(block, '_atom_site_B_iso_or_equiv')
        if has_u or has_b:
            for atom in atoms:
                atom['u_iso'] = float(next((s.u_iso for s in expanded if s.label == atom['label']), 0.0))
        else:
            for atom in atoms:
                atom['u_iso'] = None

        cell = small.cell
        sg = small.spacegroup
        sg_number = int(sg.number) if sg else int(small.spacegroup_number or 0)
        hall_number = _find_hall_number(sg, small.spacegroup_hall or (sg.hall if sg else ''))
        formula = block.find_value('_chemical_formula_sum') or block.find_value('_chemical_formula_structural') or ''
        hm = small.spacegroup_hm or (sg.hm if sg else '')
        hall_symbol = small.spacegroup_hall or (sg.hall if sg else '')
        crystal_system = (block.find_value('_symmetry_cell_setting') or block.find_value('_space_group_crystal_system') or '').strip().lower()
        systems = {'cubic':'Cubic','tetragonal':'Tetragonal','orthorhombic':'Orthorhombic','hexagonal':'Hexagonal','trigonal':'Trigonal / Rhombohedral','rhombohedral':'Trigonal / Rhombohedral','monoclinic':'Monoclinic','triclinic':'Triclinic'}
        if not crystal_system and sg_number:
            crystal_system = ('triclinic' if sg_number <= 2 else 'monoclinic' if sg_number <= 15 else 'orthorhombic' if sg_number <= 74 else 'tetragonal' if sg_number <= 142 else 'trigonal' if sg_number <= 167 else 'hexagonal' if sg_number <= 194 else 'cubic')
        lattice = {'a':float(cell.a),'b':float(cell.b),'c':float(cell.c),'alpha':float(cell.alpha),'beta':float(cell.beta),'gamma':float(cell.gamma)}
        wyckoff_values = list(block.find_values('_atom_site_Wyckoff_symbol'))
        multiplicity_values = list(block.find_values('_atom_site_symmetry_multiplicity'))
        asym = []
        for idx, site in enumerate(small.sites):
            multiplicity = int(float(multiplicity_values[idx])) if idx < len(multiplicity_values) and str(multiplicity_values[idx]).strip() not in ('.','?') else sum(1 for expanded_site in expanded if expanded_site.label == site.label)
            wyckoff = str(wyckoff_values[idx]) if idx < len(wyckoff_values) and str(wyckoff_values[idx]).strip() not in ('.','?') else None
            asym.append({'label':site.label,'element':_atom_element(site),'x':float(site.fract.x)%1,'y':float(site.fract.y)%1,'z':float(site.fract.z)%1,'occupancy':float(site.occ),'multiplicity':multiplicity,'wyckoff_symbol':wyckoff})
        meta = {'formula':formula,'space_group_number':sg_number,'space_group_symbol':hm,'hall_symbol':hall_symbol,'hall_number':hall_number,'crystal_system':systems.get(crystal_system, crystal_system),'lattice':lattice,'asymmetric_sites':asym,'unit_cell_atoms':atoms,'unit_cell_atom_count':len(atoms),'element_counts':{e:sum(a['element']==e for a in atoms) for e in sorted({a['element'] for a in atoms})},'debye_waller_applied':has_u or has_b,'debye_waller_note':'Applied from CIF Uiso/Biso' if has_u or has_b else 'Not applied: CIF has no Uiso/Biso values'}
        if not req.reflections:
            return {'success':True,'data':meta}

        # Use the exact Hall setting reported by Gemmi for the symmetry phase sum.
        sym = spglib.get_symmetry_from_database(hall_number) if hall_number else None
        if sym is None:
            raise ValueError('Could not resolve CIF Hall setting in spglib database')
        scattering = {}
        f_engine_error = None
        try:
            from abtem.parametrizations import LobatoParametrization
            lobato = LobatoParametrization()
            for element, charge in sorted({(a['element'], float(a.get('charge', 0.0))) for a in atoms}):
                try:
                    scattering[(element, charge)] = lobato.scattering_factor(element, charge=charge)
                except Exception as exc:
                    f_engine_error = f'No Lobato electron scattering-factor coefficients for {element} with charge {charge:+g}: {exc}'
                    break
        except Exception as exc:
            f_engine_error = f'Lobato electron scattering-factor engine unavailable: {exc}. Install abTEM; no X-ray fallback is permitted.'

        out=[]
        G=np.array([[lattice['a']**2,lattice['a']*lattice['b']*math.cos(math.radians(lattice['gamma'])),lattice['a']*lattice['c']*math.cos(math.radians(lattice['beta']))],
                    [lattice['a']*lattice['b']*math.cos(math.radians(lattice['gamma'])),lattice['b']**2,lattice['b']*lattice['c']*math.cos(math.radians(lattice['alpha']))],
                    [lattice['a']*lattice['c']*math.cos(math.radians(lattice['beta'])),lattice['b']*lattice['c']*math.cos(math.radians(lattice['alpha'])),lattice['c']**2]],dtype=float)
        Ginv=np.linalg.inv(G)
        for ref in req.reflections:
            h,k,l=ref.h,ref.k,ref.l
            if h==k==l==0: raise ValueError('(000) is not a valid reflection')
            hv=np.array([h,k,l],dtype=float)
            q=float(hv @ Ginv @ hv)
            if q<=0: raise ValueError(f'Invalid reciprocal metric for ({h},{k},{l})')
            d=1/math.sqrt(q); s=1/(2*d)
            re_f=0.0; im_f=0.0
            f_available = f_engine_error is None and len(scattering) == len({(a['element'], float(a.get('charge', 0.0))) for a in atoms})
            if f_available:
                for atom in atoms:
                    fj=float(np.asarray(scattering[(atom['element'], float(atom.get('charge', 0.0)))](s*s)).item())
                    if atom.get('u_iso') is not None:
                        fj *= math.exp(-8*math.pi**2*float(atom['u_iso'])*s*s)
                    phase=2*math.pi*(h*atom['x']+k*atom['y']+l*atom['z'])
                    amp=fj*atom['occupancy']
                    re_f += amp*math.cos(phase); im_f += amp*math.sin(phase)
            fmag=math.hypot(re_f,im_f) if f_available else None
            # Little-group phase sum, same symmetry criterion as /systematic-absences.
            phases=[]
            hv_int=np.array([h,k,l],dtype=int)
            for rot,trans in zip(sym['rotations'],sym['translations']):
                if np.array_equal(np.asarray(rot,dtype=int).T @ hv_int,hv_int):
                    phases.append(np.exp(2j*np.pi*float(np.dot(hv_int,trans))))
            shkl=abs(sum(phases)) if phases else 1.0
            shkl_allowed=shkl>1e-7
            f_allowed=(fmag is not None and fmag>req.f_tolerance)
            final=('Allowed' if f_allowed else 'Forbidden (Atomic Basis Extinction)') if shkl_allowed and f_available else ('Allowed (Shkl only; Fhkl unavailable)' if shkl_allowed else 'Forbidden')
            out.append({'h':h,'k':k,'l':l,'d_angstrom':d,'d_nanometer':d/10,'inverse_d2':1/(d*d),'shkl_magnitude':float(shkl),'shkl_status':'Allowed' if shkl_allowed else 'Forbidden','f_real':re_f if f_available else None,'f_imag':im_f if f_available else None,'f_magnitude':fmag,'f_intensity':fmag*fmag if f_available else None,'f_status':('Allowed' if f_allowed else 'Forbidden') if f_available else 'Not Calculated','final_status':final})
        return {'success':True,'data':{**meta,'reflections':out,'scattering_model':'Lobato electron scattering factor (abTEM)' if f_engine_error is None else None,'scattering_reference':'Lobato I, Van Dyck D. Acta Cryst A. 2014;70:636-649.','intensity_model':'Kinematic |Fhkl|^2; not an exact experimental SAED intensity','f_calculation_note':f_engine_error or 'Lobato electron scattering factors calculated successfully'}}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422,detail=f'CIF analysis failed: {exc}')
