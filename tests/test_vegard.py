import pytest
from vegard import calc_vegard_sws

def test_pure_element():
    assert calc_vegard_sws({'W': 100}) == pytest.approx(2.95)

def test_binary_equal():
    expected = 0.5 * 2.95 + 0.5 * 2.88  # W50Re50
    assert calc_vegard_sws({'W': 50, 'Re': 50}) == pytest.approx(expected)

def test_quinary():
    comp = {'Ti': 20, 'Nb': 20, 'Ta': 20, 'Mo': 20, 'W': 20}
    expected = 0.2 * (3.05 + 3.07 + 3.07 + 2.93 + 2.95)
    assert calc_vegard_sws(comp) == pytest.approx(expected)

def test_actual_csv_row():
    # DFT_0010: Nb5Ta45Mo5W45
    comp = {'Nb': 5, 'Ta': 45, 'Mo': 5, 'W': 45}
    expected = 0.05*3.07 + 0.45*3.07 + 0.05*2.93 + 0.45*2.95
    assert calc_vegard_sws(comp) == pytest.approx(expected)

def test_empty_raises():
    with pytest.raises(ValueError):
        calc_vegard_sws({})

def test_bad_sum_raises():
    with pytest.raises(ValueError):
        calc_vegard_sws({'W': 50})  # doesn't sum to 100
