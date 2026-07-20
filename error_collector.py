import os
import csv
import re
from collections import Counter

def check_emto_errors(alloy_id, stage_dir):
    folder = os.path.join(stage_dir, alloy_id)
    kgrn_dir = os.path.join(folder, 'kgrn')
    kfcd_dir = os.path.join(folder, 'kfcd')
    errors = []

    if not os.path.isdir(kgrn_dir) and not os.path.isdir(kfcd_dir):
        return errors

    # Collect all jobnames from kgrn .prn files
    kgrn_jobs = set()
    if os.path.isdir(kgrn_dir):
        for f in os.listdir(kgrn_dir):
            if f.endswith('.prn'):
                kgrn_jobs.add(f[:-4])

    # Also check kfcd for any jobnames
    kfcd_jobs = set()
    if os.path.isdir(kfcd_dir):
        for f in os.listdir(kfcd_dir):
            if f.endswith('.prn'):
                kfcd_jobs.add(f[:-4])

    all_jobs = kgrn_jobs | kfcd_jobs

    for job in sorted(all_jobs):
        sws = _extract_sws(job)

        # Check missing output
        kgrn_file = os.path.join(kgrn_dir, job + '.prn')
        kfcd_file = os.path.join(kfcd_dir, job + '.prn')

        if not os.path.isfile(kfcd_file):
            errors.append({'sws': sws, 'error_type': 'missing_output',
                           'message': f'kfcd output missing for {job}'})
            continue

        # Check SCF convergence in KGRN output (independent of kfcd content)
        if os.path.isfile(kgrn_file):
            with open(kgrn_file, 'r') as f:
                content = f.read()
            # 用正向判据，不能搜 "not converged"：KGRN 在每次 SCF 迭代里都会
            # 打印 "PATHOP: CPA equation ... not converged" 和 "Linear loop not
            # converged"，一个完全收敛的点也有几十条，搜子串会把所有成功的点
            # 全判成失败。完成标记与 run_one.sh / submit_stage.sh 保持一致。
            if 'CALCULATION FINISHED' not in content.upper():
                errors.append({'sws': sws, 'error_type': 'scf_not_converged',
                               'message': f'KGRN SCF not converged for {job}'})

        if os.path.getsize(kfcd_file) == 0:
            errors.append({'sws': sws, 'error_type': 'missing_output',
                           'message': f'kfcd output empty for {job}'})
            continue

        # Check for energy in KFCD output
        with open(kfcd_file, 'r') as f:
            content = f.read()
        if 'TOT-PBE' not in content and 'TOT-LDA' not in content:
            errors.append({'sws': sws, 'error_type': 'no_energy',
                           'message': f'No total energy found in kfcd output for {job}'})
            continue

        # Check for NaN energy
        for line in content.split('\n'):
            if 'TOT-' in line:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        en = float(parts[3])
                        if en != en:  # NaN check
                            errors.append({'sws': sws, 'error_type': 'nan_energy',
                                           'message': f'NaN energy in {job}'})
                    except ValueError:
                        errors.append({'sws': sws, 'error_type': 'nan_energy',
                                       'message': f'Unparseable energy in {job}'})

    return errors


def _extract_sws(jobname):
    parts = jobname.rsplit('_', 1)
    if len(parts) == 2:
        try:
            return float(parts[1])
        except ValueError:
            pass
    return 0.0


def write_error_report(alloy_id, alloy_name, errors, error_csv_path):
    file_exists = os.path.isfile(error_csv_path)
    with open(error_csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['DFT_ID', 'Alloy', 'SWS', 'error_type', 'message'])
        for e in errors:
            writer.writerow([alloy_id, alloy_name, e['sws'], e['error_type'], e['message']])


def summarize_errors(error_csv_path):
    if not os.path.isfile(error_csv_path):
        print("No error file found.")
        return
    counts = Counter()
    affected_ids = set()
    with open(error_csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            counts[row['error_type']] += 1
            affected_ids.add(row['DFT_ID'])
    print(f"Error summary ({len(affected_ids)} alloys affected):")
    for etype, count in counts.most_common():
        print(f"  {etype}: {count}")
