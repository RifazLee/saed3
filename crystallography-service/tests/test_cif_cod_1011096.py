from pathlib import Path
import gemmi

CIF = Path(__file__).parent / 'fixtures' / '1011096.cif'

def test_cod_1011096_cif_expands_to_full_conventional_cell():
    block = gemmi.cif.read_file(str(CIF))[0]
    small = gemmi.make_small_structure_from_block(block)
    atoms = small.get_all_unit_cell_sites()
    counts = {}
    for atom in atoms:
        counts[atom.element.name] = counts.get(atom.element.name, 0) + 1
    assert small.spacegroup.number == 225
    assert small.spacegroup.hm == 'F m -3 m'
    assert small.spacegroup.hall == '-F 4 2 3'
    assert abs(small.cell.a - 4.725) < 1e-8
    assert len(small.sites) == 2
    assert len(atoms) == 8
    assert counts == {'Cd': 4, 'O': 4}
    assert {site.label: site.charge for site in small.sites} == {'Cd1': 2.0, 'O1': -2.0}
