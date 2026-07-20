import os
import pytest
import numpy as np
from config import COARSE_N_POINTS, COARSE_RANGE
from emto_generator import parse_csv
from vegard import calc_vegard_sws

def test_vegard_sws_range_reasonable():
    csv_path = os.path.join(os.path.dirname(__file__), '..',
                            '20260718-refractory-hea-compositions-1600-highthroughput-dft.csv')
    alloys = parse_csv(csv_path)
    for alloy in alloys:
        sws = calc_vegard_sws(alloy['composition'])
        assert 2.5 < sws < 3.5, f"{alloy['id']}: SWS={sws} out of reasonable range"

def test_all_compositions_sum_to_100():
    csv_path = os.path.join(os.path.dirname(__file__), '..',
                            '20260718-refractory-hea-compositions-1600-highthroughput-dft.csv')
    alloys = parse_csv(csv_path)
    for alloy in alloys:
        total = sum(alloy['concs'])
        assert total == 100, f"{alloy['id']}: concs sum to {total}"

def test_sws_list_generation():
    center = 3.0
    sws_list = list(np.linspace(center * (1 - COARSE_RANGE),
                                center * (1 + COARSE_RANGE),
                                COARSE_N_POINTS))
    assert len(sws_list) == 6
    assert sws_list[0] == pytest.approx(center * 0.97)
    assert sws_list[-1] == pytest.approx(center * 1.03)
