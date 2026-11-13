# SAED Analyzer — CIF + Fhkl deployment

## What changed

- Material Calculation supports Manual Input (existing Shkl-only path) and CIF Upload (Shkl + Fhkl path).
- CIF is parsed by Gemmi; asymmetric-unit sites are expanded into the conventional unit cell and symmetry-equivalent duplicate coordinates are removed.
- Element identity, ionic charge, fractional coordinates, occupancy, optional Uiso/Biso, multiplicity and optional Wyckoff label are retained.
- Shkl is calculated from the exact Hall setting using spglib symmetry operations.
- Fhkl is calculated from full-cell atoms using the Lobato electron scattering-factor parameterization exposed by abTEM. Ionic charges parsed from CIF are passed to the parametrization.
- Missing displacement parameters are not invented. The material detail explicitly indicates when Debye–Waller correction was not applied.
- Only operator-selected HKL rows are inserted into `hkl_reflections`; unselected calculation rows are not persisted. The CIF source and atomic structure metadata are stored at material-version level.
- SAED validated-material references include only symmetry-Allowed rows and, for CIF materials, exclude rows with atomic-basis extinction (`final_status` must be `Allowed`).
- Material validation updates material/version validation metadata only; it does not rewrite reflection classifications or Fhkl values.

## Deployment sequence

1. Back up the MySQL database.
2. Apply `backend/migrations/002_add_cif_fhkl.sql` after the existing `001_initial.sql` and any previously deployed migration that adds `Centering-compatible`.
3. Deploy the updated Express backend. Ensure the Node process has `SPGLIB_URL` set to the private base URL of the Python service. The Express JSON body limit is 8 MB; CIF text is limited to 5 MB.
4. Deploy `crystallography-service/main.py` and install `crystallography-service/requirements.txt` in a persistent Python environment. Start with `uvicorn main:app --host 0.0.0.0 --port 8100` behind a private network or authenticated reverse proxy. Do not expose the service publicly without access controls.
5. Ensure the Express backend can reach that Python service. If the hosting plan cannot run persistent Python processes, use a VPS/private compute host and set `SPGLIB_URL` to its private HTTPS endpoint.
6. Build and deploy the updated frontend. The frontend uses the existing `VITE_API_BASE_URL` configuration.
7. Test `GET /api/health`, then log in as an operator and upload `1011096.cif`.

## CdO COD 1011096 regression fixture

The included fixture is expected to parse as:

- Formula CdO
- Space group 225, F m -3 m, Hall symbol -F 4 2 3
- Cubic lattice a=b=c=4.725 Å and angles 90°
- Two asymmetric sites (Cd and O)
- Eight expanded conventional-cell atoms: four Cd and four O
- Ionic charges Cd +2 and O -2 as read by Gemmi from the CIF type symbols

Run the parser fixture test from `crystallography-service`:

```bash
pytest -q tests/test_cif_cod_1011096.py
```

The test verifies CIF parsing and unit-cell expansion. It does not validate the numerical Fhkl engine because abTEM must be installed in the Python service environment for that calculation.

## Scientific interpretation

`Shkl` is a symmetry-phase sum for systematic absence. `Fhkl` is a full-cell atomic structure factor using electron scattering factors. `|Fhkl|²` is a kinematic theoretical intensity, not a prediction of measured SAED intensity under dynamical scattering. The selected Lobato model and its reference are stored with the material version. If abTEM or coefficients for an element/charge state are unavailable, the service preserves Shkl, marks Fhkl as Not Calculated, and labels the result as Shkl-only; it never substitutes X-ray scattering factors.

## Important

- Never upload a real `.env` file. Configure environment variables in the hosting control panel.
- Rotate any DB password or JWT secret previously exposed in a chat, archive, or repository.
- Apply the migration before deploying backend code that selects the new columns.
