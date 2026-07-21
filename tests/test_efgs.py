import math
import pytest
from efgs import estimate_ef, calc_efgs
from config import EFGS_EF_COEF, EFGS_SWS_COEF, EFGS_MARGIN


def test_estimate_ef_matches_model():
    """E_F = sum(conc * EF_COEF) + SWS_COEF * sws."""
    comp = {'W': 91, 'Re': 9}
    sws = 2.90
    expected = (0.91 * EFGS_EF_COEF['W'] + 0.09 * EFGS_EF_COEF['Re']
                + EFGS_SWS_COEF * sws)
    assert estimate_ef(comp, sws) == pytest.approx(expected)


def test_calc_efgs_adds_outward_margin_negative():
    """EFGS pushes the guess outward: negative E_F gets a more-negative EFGS."""
    comp = {'Ti': 2, 'Zr': 22, 'Hf': 26, 'Ta': 50}
    sws = 3.20
    ef = estimate_ef(comp, sws)
    assert ef < 0  # this Hf/Ta-rich point sits on the negative side
    assert calc_efgs(comp, sws) == pytest.approx(ef - EFGS_MARGIN)


def test_calc_efgs_adds_outward_margin_positive():
    """Positive E_F gets a more-positive EFGS (pushed away from zero)."""
    comp = {'Ta': 80, 'W': 20}  # Ta80W20, small positive E_F near the crossing
    sws = 2.95
    ef = estimate_ef(comp, sws)
    assert ef > 0
    assert calc_efgs(comp, sws) == pytest.approx(ef + EFGS_MARGIN)
    # and the margin lifts it clear of zero into the working range
    assert abs(calc_efgs(comp, sws)) >= EFGS_MARGIN


def test_calc_efgs_margin_matches_sign():
    """|EFGS| = |E_F| + MARGIN and sign(EFGS) == sign(E_F)."""
    for comp in ({'Ti': 100}, {'Re': 100}, {'V': 60, 'Nb': 40}):
        ef = estimate_ef(comp, 3.0)
        efgs = calc_efgs(comp, 3.0)
        assert math.copysign(1, efgs) == math.copysign(1, ef)
        assert abs(efgs) == pytest.approx(abs(ef) + EFGS_MARGIN)


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
