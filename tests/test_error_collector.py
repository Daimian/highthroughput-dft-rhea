import os
import pytest
from error_collector import check_emto_errors, write_error_report, summarize_errors

def _write_kfcd_prn(folder, jobname, content):
    kfcd_dir = os.path.join(folder, 'kfcd')
    os.makedirs(kfcd_dir, exist_ok=True)
    with open(os.path.join(kfcd_dir, jobname + '.prn'), 'w') as f:
        f.write(content)

def _write_kgrn_prn(folder, jobname, content):
    kgrn_dir = os.path.join(folder, 'kgrn')
    os.makedirs(kgrn_dir, exist_ok=True)
    with open(os.path.join(kgrn_dir, jobname + '.prn'), 'w') as f:
        f.write(content)

def test_no_errors_when_output_exists(tmp_path):
    folder = str(tmp_path / 'DFT_0001')
    jobname = 'DFT_0001_2.940000'
    _write_kfcd_prn(folder, jobname, 'TOT-PBE    -123.456  0.000  -61.728\n')
    _write_kgrn_prn(folder, jobname, 'Converged in 50 iterations\n')
    errors = check_emto_errors('DFT_0001', str(tmp_path))
    assert errors == []

def test_missing_kfcd_output(tmp_path):
    folder = str(tmp_path / 'DFT_0001')
    os.makedirs(os.path.join(folder, 'kgrn'), exist_ok=True)
    os.makedirs(os.path.join(folder, 'kfcd'), exist_ok=True)
    # Write a KGRN file but no matching KFCD
    _write_kgrn_prn(folder, 'DFT_0001_2.940000', 'some output\n')
    errors = check_emto_errors('DFT_0001', str(tmp_path))
    assert len(errors) >= 1
    assert any(e['error_type'] == 'missing_output' for e in errors)

def test_scf_not_converged(tmp_path):
    folder = str(tmp_path / 'DFT_0001')
    content = 'NOT CONVERGED\nSome other line\n'
    _write_kgrn_prn(folder, 'DFT_0001_2.940000', content)
    _write_kfcd_prn(folder, 'DFT_0001_2.940000', '')
    errors = check_emto_errors('DFT_0001', str(tmp_path))
    assert any(e['error_type'] == 'scf_not_converged' for e in errors)

def _finished_point(folder, aid, sws, energy):
    """A cleanly-converged point: KGRN completion marker + a KFCD total energy."""
    job = f'{aid}_{sws:.6f}'
    _write_kgrn_prn(folder, job, 'KGRN CALCULATION FINISHED\n')
    _write_kfcd_prn(folder, job,
                    f'TOT-PBE  {energy:.6f} (Ry)  {energy:.6f} (Ry/site)   '
                    f'S=  {sws:.6f} Bohr\n')


def test_outlier_energy_flagged(tmp_path):
    """A converged point tens of Ry off the alloy median is flagged."""
    folder = str(tmp_path / 'DFT_9999')
    for sws, e in [(3.10, -25094.94), (3.14, -25094.93),
                   (3.18, -25094.92), (3.22, -25060.16)]:  # last is spurious
        _finished_point(folder, 'DFT_9999', sws, e)
    errors = check_emto_errors('DFT_9999', str(tmp_path))
    outliers = [e for e in errors if e['error_type'] == 'outlier_energy']
    assert len(outliers) == 1
    assert outliers[0]['sws'] == 3.22


def test_normal_eos_spread_not_flagged(tmp_path):
    """Milli-Ry EOS variation across the window must not trip the guard."""
    folder = str(tmp_path / 'DFT_9998')
    for sws, e in [(3.10, -21341.3620), (3.14, -21341.3650),
                   (3.18, -21341.3657), (3.22, -21341.3592)]:
        _finished_point(folder, 'DFT_9998', sws, e)
    errors = check_emto_errors('DFT_9998', str(tmp_path))
    assert not any(e['error_type'] == 'outlier_energy' for e in errors)


def test_outlier_needs_three_points(tmp_path):
    """With only two points the median can't identify which one is wrong."""
    folder = str(tmp_path / 'DFT_9997')
    for sws, e in [(3.10, -100.0), (3.14, -135.0)]:
        _finished_point(folder, 'DFT_9997', sws, e)
    errors = check_emto_errors('DFT_9997', str(tmp_path))
    assert not any(e['error_type'] == 'outlier_energy' for e in errors)


def test_write_and_summarize(tmp_path, capsys):
    error_csv = str(tmp_path / 'errors.csv')
    errors = [
        {'sws': 2.94, 'error_type': 'scf_not_converged', 'message': 'not converged'},
        {'sws': 2.96, 'error_type': 'missing_output', 'message': 'kfcd output missing'},
    ]
    write_error_report('DFT_0001', 'W91Re9', errors, error_csv)
    write_error_report('DFT_0002', 'W95Re5',
                       [{'sws': 2.95, 'error_type': 'scf_not_converged', 'message': 'not converged'}],
                       error_csv)
    summarize_errors(error_csv)
    captured = capsys.readouterr()
    assert 'scf_not_converged' in captured.out
    assert '2' in captured.out  # 2 scf errors
