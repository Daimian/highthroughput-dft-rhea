import os
import csv
import re
from collections import Counter

# Energy gap that separates distinct electronic states. Points of one physical
# EOS vary by milli-Ry across the window; a point that converged to a different
# (metastable/spurious) state sits >= ~0.4 Ry away (observed 0.4-6.7 Ry). This
# threshold must be well above the real spread and below the smallest spurious
# gap so the two never merge and a real EOS is never split.
EOS_STATE_GAP_RY = 0.1


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

    point_energies = []  # (sws, energy) for points with a finite total energy

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

        # Check for NaN energy over every TOT- line, and record the one canonical
        # total energy for outlier detection. KFCD prints a TOT- line per XC
        # functional (LDA/PBE/P07/AM5/LAG); the pipeline uses PBE, so key off
        # TOT-PBE (falling back to TOT-LDA) rather than all TOT- lines.
        pbe_energy = None
        lda_energy = None
        for line in content.split('\n'):
            if 'TOT-' in line:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        en = float(parts[3])
                    except ValueError:
                        errors.append({'sws': sws, 'error_type': 'nan_energy',
                                       'message': f'Unparseable energy in {job}'})
                        continue
                    if en != en:  # NaN check
                        errors.append({'sws': sws, 'error_type': 'nan_energy',
                                       'message': f'NaN energy in {job}'})
                    elif parts[0] == 'TOT-PBE':
                        pbe_energy = en
                    elif parts[0] == 'TOT-LDA':
                        lda_energy = en
        canonical = pbe_energy if pbe_energy is not None else lda_energy
        if canonical is not None:
            point_energies.append((sws, canonical))

    # Outlier-energy guard: a point may hit the completion marker yet converge to
    # a metastable/spurious electronic state, ABOVE or BELOW the true EOS energy
    # (observed both: +0.4..+35 Ry and -0.4..-0.8 Ry). Cluster the energies by
    # EOS_STATE_GAP_RY gaps and keep the most populated cluster -- the consistent
    # EOS family -- flagging every other point. Breaking ties toward the lower
    # cluster keeps the ground state on the rare even split. Population, not
    # lowest energy, is the discriminant: a single spurious point can sit below
    # the whole EOS family, so "keep the lowest cluster" would keep the wrong one.
    if len(point_energies) >= 3:
        ordered = sorted(point_energies, key=lambda p: p[1])
        clusters = [[ordered[0]]]
        for sws, en in ordered[1:]:
            if en - clusters[-1][-1][1] > EOS_STATE_GAP_RY:
                clusters.append([(sws, en)])
            else:
                clusters[-1].append((sws, en))
        keep = max(clusters, key=lambda c: (len(c), -c[0][1]))
        keep_lo, keep_hi = keep[0][1], keep[-1][1]
        for sws, en in point_energies:
            if en < keep_lo or en > keep_hi:
                errors.append({'sws': sws, 'error_type': 'outlier_energy',
                               'message': f'total energy {en:.3f} Ry lies outside '
                                          f'the main EOS cluster '
                                          f'[{keep_lo:.3f}, {keep_hi:.3f}] Ry'})

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
