import os
import pytest
from eos_analysis import (check_coarse_fit, _get_sws_from_dir,
                          _extract_total_energy, _read_point_energies,
                          _fit_failed_retry_info)
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


# --- fit-failed re-centering ------------------------------------------------

# The energy field lives at index 3 (Ry/site), matching error_collector:
#   TOT-PBE  <total> (Ry)  <per-site> (Ry/site)  S= <sws> Bohr
_TOT_LINE = ('    TOT-PBE  {e:.6f} (Ry)  {e:.6f} (Ry/site)   S=  {s} Bohr\n')


def _make_alloy_with_energies(tmp_path, alloy_id, sws_to_energy):
    """Create <alloy>/kfcd/<job>.prn files carrying the given energies."""
    kfcd_dir = tmp_path / alloy_id / 'kfcd'
    kfcd_dir.mkdir(parents=True)
    for sws, energy in sws_to_energy.items():
        with open(kfcd_dir / f'{alloy_id}_{sws:.6f}.prn', 'w') as f:
            f.write('some header\n')
            f.write(_TOT_LINE.format(e=energy, s=f'{sws:.6f}'))
    return str(tmp_path / alloy_id)


def test_extract_total_energy_reads_field_3(tmp_path):
    p = tmp_path / 'x.prn'
    with open(p, 'w') as f:
        f.write(_TOT_LINE.format(e=-6156.192213, s='3.085396'))
    assert _extract_total_energy(str(p)) == pytest.approx(-6156.192213)


def test_extract_total_energy_missing_line(tmp_path):
    p = tmp_path / 'x.prn'
    p.write_text('no energy here\n')
    assert _extract_total_energy(str(p)) is None


def test_read_point_energies_maps_sws(tmp_path):
    alloy_id = 'DFT_0001'
    d = _make_alloy_with_energies(tmp_path, alloy_id,
                                  {2.90: -100.0, 2.95: -101.0, 3.00: -100.5})
    energies = _read_point_energies(d, alloy_id)
    assert energies == {2.9: -100.0, 2.95: -101.0, 3.0: -100.5}


def test_fit_failed_recenter_interior(tmp_path):
    """Lowest energy at an interior point -> re-center exactly on it."""
    alloy_id = 'DFT_0001'
    sws_list = [2.80, 2.85, 2.90, 2.95, 3.00, 3.05]
    d = _make_alloy_with_energies(tmp_path, alloy_id,
        {2.80: -9, 2.85: -9.5, 2.90: -10, 2.95: -9.4, 3.00: -9, 3.05: -8})
    info = _fit_failed_retry_info(d, alloy_id, sws_list)
    assert 'interior' in info['reason']
    assert info['new_sws_center'] == pytest.approx(2.90)


def test_fit_failed_recenter_lower_edge(tmp_path):
    """Lowest energy at the lowest sampled point -> shift down half the range."""
    alloy_id = 'DFT_0001'
    sws_list = [2.80, 2.85, 2.90, 2.95, 3.00, 3.05]
    d = _make_alloy_with_energies(tmp_path, alloy_id,
        {2.80: -12, 2.85: -11, 2.90: -10, 2.95: -9, 3.00: -8, 3.05: -7})
    info = _fit_failed_retry_info(d, alloy_id, sws_list)
    assert 'lower_edge' in info['reason']
    # center 2.925, half range 0.125 -> 2.80
    assert info['new_sws_center'] == pytest.approx(2.80)


def test_fit_failed_recenter_upper_edge(tmp_path):
    """Lowest energy at the highest sampled point -> shift up half the range."""
    alloy_id = 'DFT_0001'
    sws_list = [2.80, 2.85, 2.90, 2.95, 3.00, 3.05]
    d = _make_alloy_with_energies(tmp_path, alloy_id,
        {2.80: -7, 2.85: -8, 2.90: -9, 2.95: -10, 3.00: -11, 3.05: -12})
    info = _fit_failed_retry_info(d, alloy_id, sws_list)
    assert 'upper_edge' in info['reason']
    assert info['new_sws_center'] == pytest.approx(3.05)


def test_fit_failed_no_energies_returns_none(tmp_path):
    """No readable energies -> None so the caller falls back to a no-shift row."""
    alloy_id = 'DFT_0001'
    (tmp_path / alloy_id).mkdir()
    info = _fit_failed_retry_info(str(tmp_path / alloy_id), alloy_id,
                                 [2.80, 2.90, 3.00])
    assert info is None
