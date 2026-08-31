import os
import pytest
from emto_generator import parse_csv, _params_for
from config import (EMTO_PARAMS, DEEP_TA_THRESHOLD, DEEP_TA_DEPTH, DEEP_TA_AMIX,
                    DEEP_TA_ALLOYS, AMIX_ONLY_ALLOYS, MIXED_HF_DEPTH,
                    MIXED_HF_ALLOYS)


def test_params_for_deep_ta_gets_depth_and_amix():
    p = _params_for('DFT_0001', {'Hf': 1, 'Ta': 81, 'W': 16, 'Re': 2})
    assert p['depth'] == DEEP_TA_DEPTH == 0.80
    assert p['amix'] == DEEP_TA_AMIX == 0.02


def test_params_for_at_threshold_is_inclusive():
    at = _params_for('X', {'Ta': DEEP_TA_THRESHOLD, 'W': 70})       # Ta = 30
    assert at['depth'] == 0.80 and at['amix'] == 0.02
    below = _params_for('X', {'Ta': DEEP_TA_THRESHOLD - 1, 'W': 71})  # Ta = 29
    assert below['depth'] == 0.95 and 'amix' not in below


def test_params_for_listed_alloy_gets_full_override():
    aid = next(iter(DEEP_TA_ALLOYS))
    p = _params_for(aid, {'Ta': 25, 'V': 35, 'W': 40})  # Ta<30 but listed
    assert p['depth'] == DEEP_TA_DEPTH == 0.80
    assert p['amix'] == DEEP_TA_AMIX == 0.02


def test_params_for_low_ta_keeps_defaults():
    p = _params_for('DFT_0001', {'W': 91, 'Re': 9})
    assert p['depth'] == EMTO_PARAMS['depth'] == 0.95
    assert 'amix' not in p  # pyemto default AMIX untouched


def test_params_for_amix_only_alloy_keeps_depth():
    aid = next(iter(AMIX_ONLY_ALLOYS))
    p = _params_for(aid, {'Hf': 20, 'V': 35, 'Zr': 20, 'W': 25})  # no Ta
    assert p['amix'] == DEEP_TA_AMIX == 0.02
    assert p['depth'] == EMTO_PARAMS['depth'] == 0.95  # depth NOT lowered


def test_params_for_full_override_beats_amix_only():
    # an id in both lists must get the full override (depth lowered too)
    assert not (DEEP_TA_ALLOYS & AMIX_ONLY_ALLOYS)  # they are disjoint by design
    aid = next(iter(DEEP_TA_ALLOYS))
    p = _params_for(aid, {'Ta': 5, 'V': 35, 'W': 60})
    assert p['depth'] == DEEP_TA_DEPTH == 0.80
    assert p['amix'] == DEEP_TA_AMIX == 0.02


def test_params_for_mixed_hf_uses_depth_090():
    from config import HF_D80_ALLOYS
    aid = next(iter(MIXED_HF_ALLOYS - HF_D80_ALLOYS))  # one that stayed at 0.90
    p = _params_for(aid, {'Hf': 40, 'Nb': 25, 'Ta': 25, 'W': 10})  # Ta<30
    assert p['depth'] == MIXED_HF_DEPTH == 0.90  # deepest that converges distortions
    assert p['amix'] == DEEP_TA_AMIX == 0.02


def test_override_base_tiers_disjoint():
    # the three base tiers partition the alloys
    assert not (DEEP_TA_ALLOYS & MIXED_HF_ALLOYS)
    assert not (DEEP_TA_ALLOYS & AMIX_ONLY_ALLOYS)
    assert not (MIXED_HF_ALLOYS & AMIX_ONLY_ALLOYS)


def test_d70_tier_wins_and_uses_depth070():
    from config import D70_ALLOYS
    for aid in list(D70_ALLOYS)[:5]:
        p = _params_for(aid, {'V': 40, 'Ta': 40, 'Mo': 5, 'W': 15})
        assert p['depth'] == 0.70 and p['amix'] == 0.02  # top precedence


def test_hf_scatter_a01_uses_amix001():
    from config import HF_SCATTER_A01_ALLOYS, D70_ALLOYS
    assert len(HF_SCATTER_A01_ALLOYS) == 4
    assert not (HF_SCATTER_A01_ALLOYS & D70_ALLOYS)  # D70 has higher precedence
    for aid in HF_SCATTER_A01_ALLOYS:
        p = _params_for(aid, {'Hf': 40, 'Ta': 30, 'W': 30})  # Ta>=30 but amix0.01 wins
        assert p['depth'] == 0.80 and p['amix'] == 0.01


def test_iex_override_applied_on_top_of_tier():
    from config import IEX_OVERRIDE
    assert IEX_OVERRIDE['DFT_0198'] == 3
    p = _params_for('DFT_0198', {'Hf': 2, 'Ta': 90, 'W': 3, 'Re': 5})  # Ta>=30 tier
    assert p['depth'] == 0.80 and p['amix'] == 0.02  # from the Ta>=30 tier
    assert p['iex'] == 3  # VWN, overriding the default IEX=4
    # alloys without an override keep pyemto's default IEX (not set here)
    assert 'iex' not in _params_for('DFT_0001', {'W': 91, 'Re': 9})


def test_hf_d80_fallback_wins_and_uses_depth080():
    from config import HF_D80_ALLOYS, D70_ALLOYS
    # HF_D80 is a fallback overlay on MIXED_HF/AMIX_ONLY: it must win (depth0.80),
    # except where D70 (top tier) overrides it further to 0.70.
    assert HF_D80_ALLOYS & (MIXED_HF_ALLOYS | AMIX_ONLY_ALLOYS)  # overlaps by design
    for aid in list(HF_D80_ALLOYS - D70_ALLOYS)[:5]:
        p = _params_for(aid, {'Hf': 40, 'Ta': 20, 'W': 40})
        assert p['depth'] == 0.80 and p['amix'] == 0.02


def test_params_for_none_composition_keeps_default():
    assert _params_for('DFT_0001', None)['depth'] == 0.95


def test_params_for_does_not_mutate_emto_params():
    _params_for('DFT_0001', {'Ta': 90, 'W': 10})
    assert EMTO_PARAMS['depth'] == 0.95  # global untouched
    assert 'amix' not in EMTO_PARAMS

def test_parse_csv():
    csv_path = os.path.join(os.path.dirname(__file__), '..',
                            '20260718-refractory-hea-compositions-1600-highthroughput-dft.csv')
    alloys = parse_csv(csv_path)
    # NOTE: the source CSV contains 1598 data rows (DFT_0001..DFT_1598),
    # not 1597 as originally assumed in the brief.
    assert len(alloys) == 1598

    first = alloys[0]
    assert first['id'] == 'DFT_0001'
    assert first['alloy'] == 'W91Re9'
    assert first['atoms'] == ['W', 'Re']
    assert first['concs'] == [91, 9]
    assert first['composition'] == {'W': 91, 'Re': 9}

    # Check a multi-component alloy
    dft10 = alloys[9]  # DFT_0010
    assert dft10['id'] == 'DFT_0010'
    assert dft10['alloy'] == 'Nb5Ta45Mo5W45'
    assert set(dft10['atoms']) == {'Nb', 'Ta', 'Mo', 'W'}
    assert sum(dft10['concs']) == 100


import tempfile
import numpy as np
from emto_generator import generate_eos_inputs

def test_generate_eos_inputs_creates_files(tmp_path):
    # This test requires a latpath with bcc structure files.
    # Use a dummy latpath — pyemto will create the folder structure
    # and KGRN/KFCD input files even without actual structure output files.
    latpath = str(tmp_path / "lat")
    os.makedirs(latpath, exist_ok=True)
    stage_dir = str(tmp_path / "stage1")

    sws_list = list(np.linspace(2.85, 3.05, 6))
    generate_eos_inputs(
        alloy_id='DFT_0001',
        atoms=['W', 'Re'],
        concs=[91, 9],
        sws_list=sws_list,
        stage_dir=stage_dir,
        latpath=latpath,
    )

    alloy_dir = os.path.join(stage_dir, 'DFT_0001')
    assert os.path.isdir(alloy_dir)
    # Check KGRN input files were created (one per SWS point).
    # NOTE: the installed pyemto version writes '{jobname}_{sws}.kgrn'
    # files directly into the alloy folder rather than into a 'kgrn/'
    # subdirectory with '.dat' extensions as originally assumed.
    kgrn_files = [f for f in os.listdir(alloy_dir) if f.endswith('.kgrn')]
    assert len(kgrn_files) == 6
