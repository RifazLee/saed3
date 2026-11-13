from pathlib import Path
import pytest

pytest.importorskip('spglib')
pytest.importorskip('abtem')
from main import CifAnalyzeRequest, cif_analyze

CIF_TEXT = (Path(__file__).parent / 'fixtures' / '1011096.cif').read_text()


def test_cdo_fcc_reflection_benchmark_with_lobato_electron_factors():
    hkl = [(1, 0, 0), (1, 1, 0), (1, 1, 1), (2, 0, 0), (2, 2, 0), (2, 2, 2), (3, 1, 1)]
    result = cif_analyze(CifAnalyzeRequest(
        cif_text=CIF_TEXT,
        reflections=[{'h': h, 'k': k, 'l': l} for h, k, l in hkl],
    ))['data']
    rows = {(r['h'], r['k'], r['l']): r for r in result['reflections']}
    assert rows[(1, 0, 0)]['shkl_status'] == 'Forbidden'
    assert rows[(1, 1, 0)]['shkl_status'] == 'Forbidden'
    for key in [(1, 1, 1), (2, 0, 0), (2, 2, 0), (2, 2, 2), (3, 1, 1)]:
        assert rows[key]['shkl_status'] == 'Allowed'
        assert rows[key]['f_status'] == 'Allowed'
        assert rows[key]['f_magnitude'] > 0
        assert rows[key]['f_intensity'] == pytest.approx(rows[key]['f_magnitude'] ** 2)
