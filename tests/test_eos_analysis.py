import os
import pytest
from eos_analysis import check_coarse_fit, _get_sws_from_dir
from error_collector import _extract_sws


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


def _touch(path):
    open(path, 'w').close()


def test_get_sws_from_dir_reads_prn_not_dat(tmp_path):
    alloy_id = 'DFT_0001'
    kgrn_dir = tmp_path / alloy_id / 'kgrn'
    kgrn_dir.mkdir(parents=True)

    # A real completed KGRN point: .atm/.chd/.pot/.prn/.zms, no .dat.
    for ext in ('atm', 'chd', 'pot', 'prn', 'zms'):
        _touch(kgrn_dir / f'{alloy_id}_2.855389.{ext}')

    # More SWS points, plus a stray .dat that must NOT be picked up.
    _touch(kgrn_dir / f'{alloy_id}_2.900000.prn')
    _touch(kgrn_dir / f'{alloy_id}_2.950000.prn')
    _touch(kgrn_dir / f'{alloy_id}_3.000000.dat')

    sws_list = _get_sws_from_dir(str(tmp_path / alloy_id), alloy_id)

    assert sws_list == sorted(sws_list)
    assert 3.0 not in sws_list
    assert sws_list == [2.855389, 2.9, 2.95]


def test_get_sws_from_dir_skips_unparseable_tail(tmp_path):
    alloy_id = 'DFT_0001'
    kgrn_dir = tmp_path / alloy_id / 'kgrn'
    kgrn_dir.mkdir(parents=True)

    _touch(kgrn_dir / f'{alloy_id}_2.900000.prn')
    _touch(kgrn_dir / f'{alloy_id}_bogus.prn')

    sws_list = _get_sws_from_dir(str(tmp_path / alloy_id), alloy_id)

    assert sws_list == [2.9]


def test_get_sws_from_dir_missing_kgrn_dir(tmp_path):
    alloy_id = 'DFT_0001'
    sws_list = _get_sws_from_dir(str(tmp_path / alloy_id), alloy_id)
    assert sws_list == []


def test_get_sws_from_dir_agrees_with_extract_sws(tmp_path):
    """The SWS values _get_sws_from_dir discovers must compare equal to
    what error_collector._extract_sws parses from the matching jobname, so
    that fit_eos's `s not in error_sws` intersection actually excludes
    failed points instead of silently letting them through."""
    alloy_id = 'DFT_0001'
    kgrn_dir = tmp_path / alloy_id / 'kgrn'
    kgrn_dir.mkdir(parents=True)

    jobnames = [f'{alloy_id}_2.855389', f'{alloy_id}_2.900000', f'{alloy_id}_2.950000']
    for job in jobnames:
        _touch(kgrn_dir / f'{job}.prn')

    sws_list = _get_sws_from_dir(str(tmp_path / alloy_id), alloy_id)
    expected = sorted(_extract_sws(job) for job in jobnames)
    assert sws_list == expected
