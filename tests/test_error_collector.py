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
