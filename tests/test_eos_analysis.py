import pytest
from eos_analysis import check_coarse_fit


def test_good_fit_returns_none():
    sws_list = [2.80, 2.84, 2.88, 2.92, 2.96, 3.00]
    result = check_coarse_fit(sws0=2.90, sws_list=sws_list)
    assert result is None


def test_minimum_at_lower_edge():
    sws_list = [2.80, 2.84, 2.88, 2.92, 2.96, 3.00]
    result = check_coarse_fit(sws0=2.805, sws_list=sws_list)
    assert result is not None
    assert result['new_sws_center'] < 2.90  # shifted lower
    assert 'lower' in result['reason'] or 'edge' in result['reason']


def test_minimum_at_upper_edge():
    sws_list = [2.80, 2.84, 2.88, 2.92, 2.96, 3.00]
    result = check_coarse_fit(sws0=2.998, sws_list=sws_list)
    assert result is not None
    assert result['new_sws_center'] > 2.90  # shifted higher


def test_minimum_outside_range():
    sws_list = [2.80, 2.84, 2.88, 2.92, 2.96, 3.00]
    result = check_coarse_fit(sws0=3.05, sws_list=sws_list)
    assert result is not None
