# SAED Analyzer CIF + Fhkl feature

This source package includes the integrated CIF upload workflow, Python crystallography endpoint, backend persistence, migration, and Material Detail display.

Start with `CIF_FHKL_DEPLOYMENT.md` for deployment steps and scientific limitations.

Main changes:
- `src/pages/MaterialPage.tsx`: Manual/CIF input modes, CIF upload/preview, Shkl/Fhkl result columns, selection and filters.
- `src/App.tsx`: CIF-aware save pipeline; stores only selected HKL reflection rows and excludes temporary unselected HKLs from version metadata.
- `src/pages/MaterialDetailPage.tsx`: CIF atomic-site preview and saved Fhkl result display.
- `src/lib/api.ts`: API types for Fhkl fields.
- `backend/src/routes/material.routes.js`: authenticated CIF analysis proxy, version metadata persistence, Fhkl columns, final-status filtering for validated analysis references.
- `backend/migrations/002_add_cif_fhkl.sql`: MySQL schema update.
- `crystallography-service/main.py`: Gemmi CIF parsing, full-cell expansion, spglib symmetry phase sum, and abTEM Lobato electron scattering-factor calculation.
- `crystallography-service/tests/`: COD CdO parser and Fhkl regression tests.

Run backend tests from `backend/` using `npm test`. Run Python tests from `crystallography-service/` using `pytest -q tests/` after installing `requirements.txt`.
