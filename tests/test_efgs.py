import pytest
from efgs import estimate_ef, calc_efgs
from config import EFGS_EF_COEF, EFGS_SWS_COEF


def test_estimate_ef_matches_model():
    """E_F = sum(conc * EF_COEF) + SWS_COEF * sws."""
    comp = {'W': 91, 'Re': 9}
    sws = 2.90
    expected = (0.91 * EFGS_EF_COEF['W'] + 0.09 * EFGS_EF_COEF['Re']
                + EFGS_SWS_COEF * sws)
    assert estimate_ef(comp, sws) == pytest.approx(expected)


def test_calc_efgs_is_estimate_ef_no_scale():
    """EFGS is taken directly as the predicted E_F -- no margin factor."""
    comp = {'Ti': 2, 'Zr': 22, 'Hf': 26, 'Ta': 50}
    sws = 3.20
    assert calc_efgs(comp, sws) == estimate_ef(comp, sws)


def test_efgs_is_volume_dependent():
    """Two sws values differ by exactly EFGS_SWS_COEF * delta_sws."""
    comp = {'Ta': 50, 'Hf': 50}
    a = estimate_ef(comp, 3.10)
    b = estimate_ef(comp, 3.20)
    assert (b - a) == pytest.approx(EFGS_SWS_COEF * 0.10)


def test_pure_element_is_coef_plus_volume():
    assert estimate_ef({'Ta': 100}, 3.0) == pytest.approx(
        EFGS_EF_COEF['Ta'] + EFGS_SWS_COEF * 3.0)


def test_empty_composition_raises():
    with pytest.raises(ValueError):
        estimate_ef({}, 3.0)


def test_bad_concentration_sum_raises():
    with pytest.raises(ValueError):
        estimate_ef({'Ta': 50, 'W': 30}, 3.0)
