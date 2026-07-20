import os
import csv
import pyemto
from config import EMTO_PARAMS, COARSE_RANGE, RESULTS_DIR
from error_collector import check_emto_errors, write_error_report


def fit_eos(alloy_id, sws_list, stage_dir, atoms, concs):
    """Fit the EOS for an alloy using existing EMTO output files.

    Returns ((sws0, B0, e0, grun), errors) where the first element is
    None if the fit could not be produced.
    """
    folder = os.path.join(stage_dir, alloy_id)

    errors = check_emto_errors(alloy_id, stage_dir)
    error_sws = {e['sws'] for e in errors}
    valid_sws = [s for s in sws_list if s not in error_sws]

    if len(valid_sws) < 4:
        return None, errors

    concs_frac = [c / 100.0 for c in concs]
    splts = [0.0] * len(atoms)

    try:
        system = pyemto.System(folder=folder)
        system.bulk(
            jobname=alloy_id,
            atoms=atoms,
            concs=concs_frac,
            splts=splts,
            sws=sws_list[0],
            **EMTO_PARAMS,
        )
        result = system.lattice_constants_analyze(sws=valid_sws, prn=False)
        sws0, B0, e0, grun = result
    except Exception:
        return None, errors

    if B0 <= 0 or B0 > 1000:
        return None, errors

    return (sws0, B0, e0, grun), errors


def check_coarse_fit(sws0, sws_list):
    """Validate that a fitted equilibrium sws0 lies safely within the
    sampled sws range. Returns None if the fit is good, otherwise a dict
    describing how to re-center the sws range for a retry.
    """
    sws_min = min(sws_list)
    sws_max = max(sws_list)
    sws_range = sws_max - sws_min
    sws_center = (sws_min + sws_max) / 2.0
    edge_threshold = 0.005 * sws_center  # 0.5% of center

    if sws0 < sws_min:
        new_center = sws_center - sws_range * 0.5
        return {'new_sws_center': new_center,
                'reason': f'minimum_below_range (sws0={sws0:.4f} < {sws_min:.4f})'}

    if sws0 > sws_max:
        new_center = sws_center + sws_range * 0.5
        return {'new_sws_center': new_center,
                'reason': f'minimum_above_range (sws0={sws0:.4f} > {sws_max:.4f})'}

    if sws0 - sws_min < edge_threshold:
        new_center = sws_center - sws_range * 0.5
        return {'new_sws_center': new_center,
                'reason': f'minimum_at_lower_edge (sws0={sws0:.4f})'}

    if sws_max - sws0 < edge_threshold:
        new_center = sws_center + sws_range * 0.5
        return {'new_sws_center': new_center,
                'reason': f'minimum_at_upper_edge (sws0={sws0:.4f})'}

    return None


def _load_existing_ids(csv_path):
    ids = set()
    if os.path.isfile(csv_path):
        with open(csv_path, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ids.add(row['DFT_ID'])
    return ids


def analyze_all(stage, result_csv_path, error_csv_path, retry_csv_path, alloys):
    """Run fit_eos + check_coarse_fit over all alloys and write result,
    error, and (optional) retry CSV reports.

    `alloys` is expected to be the list of dicts produced by
    emto_generator.parse_csv, i.e. each entry has 'id', 'alloy', 'atoms',
    'concs', 'composition'.
    """
    from config import STAGE_DIRS

    stage_dir = STAGE_DIRS[stage]

    os.makedirs(os.path.dirname(result_csv_path) or '.', exist_ok=True)
    existing = _load_existing_ids(result_csv_path)

    n_success = 0
    n_error = 0
    n_retry = 0

    for alloy in alloys:
        alloy_id = alloy['id']
        if alloy_id in existing:
            n_success += 1
            continue

        alloy_dir = os.path.join(stage_dir, alloy_id)
        if not os.path.isdir(alloy_dir):
            continue

        sws_list = _get_sws_from_dir(alloy_dir, alloy_id)
        if not sws_list:
            continue

        result, errors = fit_eos(alloy_id, sws_list, stage_dir,
                                  alloy['atoms'], alloy['concs'])

        if errors:
            write_error_report(alloy_id, alloy['alloy'], errors, error_csv_path)
            n_error += len(errors)

        if result is None:
            if retry_csv_path is not None:
                _write_retry_entry(alloy_id, alloy['alloy'], sws_list, retry_csv_path)
                n_retry += 1
            continue

        sws0, B0, e0, grun = result

        # Check if coarse fit minimum is at edge (stage 1 only)
        if retry_csv_path is not None:
            retry_info = check_coarse_fit(sws0, sws_list)
            if retry_info is not None:
                _write_retry_entry(alloy_id, alloy['alloy'], sws_list,
                                   retry_csv_path, retry_info)
                n_retry += 1
                print(f"WARNING: {alloy_id} ({alloy['alloy']}): {retry_info['reason']}")
                continue

        _append_result(result_csv_path, alloy_id, alloy['alloy'], sws0, B0)
        n_success += 1

    print(f"\nAnalysis complete: {n_success} succeeded, {n_error} errors, {n_retry} need retry")


def _get_sws_from_dir(alloy_dir, alloy_id):
    kgrn_dir = os.path.join(alloy_dir, 'kgrn')
    if not os.path.isdir(kgrn_dir):
        return []
    sws_list = []
    prefix = alloy_id + '_'
    for f in sorted(os.listdir(kgrn_dir)):
        if f.startswith(prefix) and f.endswith('.dat'):
            try:
                sws = float(f[len(prefix):-4])
                sws_list.append(sws)
            except ValueError:
                pass
    return sws_list


def _append_result(csv_path, alloy_id, alloy_name, sws0, B0):
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['DFT_ID', 'Alloy', 'SWS0', 'B0'])
        writer.writerow([alloy_id, alloy_name, f'{sws0:.6f}', f'{B0:.2f}'])


def _write_retry_entry(alloy_id, alloy_name, sws_list, retry_csv_path,
                       retry_info=None):
    file_exists = os.path.isfile(retry_csv_path)
    old_center = (min(sws_list) + max(sws_list)) / 2.0
    if retry_info:
        new_center = retry_info['new_sws_center']
        reason = retry_info['reason']
    else:
        new_center = old_center
        reason = 'fit_failed'

    # Determine retry round
    retry_round = 1
    if file_exists:
        with open(retry_csv_path, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['DFT_ID'] == alloy_id:
                    retry_round = int(row['retry_round']) + 1

    with open(retry_csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['DFT_ID', 'Alloy', 'old_sws_center', 'new_sws_center',
                             'reason', 'retry_round'])
        writer.writerow([alloy_id, alloy_name, f'{old_center:.6f}',
                         f'{new_center:.6f}', reason, retry_round])
