import os
import csv
import re
import sys
from io import StringIO
import numpy as np
import pyemto
from config import (EMTO_PARAMS, ELASTIC_MIN_PTS, ELASTIC_OUTLIER_GAP_RY,
                    ELASTIC_OUTLIER_FACTOR, ELASTIC_OUTLIER_FLOOR_RY)
from error_collector import check_emto_errors, write_error_report


def calc_mechanical_properties(C11, C12, C44):
    # Polycrystalline averages are only physically meaningful for a
    # mechanically stable crystal (c' = (C11-C12)/2 > 0). For Born-unstable
    # alloys (c' <= 0) the Reuss/Hill shear, Hv and anisotropy blow up or go
    # complex; emit NaN for those rather than poison the CSV. B and Cauchy
    # pressure stay well-defined either way.
    def _nan(*_):
        return float('nan')

    B = (C11 + 2 * C12) / 3.0
    Cauchy = C12 - C44
    G_V = (C11 - C12 + 3 * C44) / 5.0
    denom_R = 4 * C44 + 3 * (C11 - C12)
    G_R = 5 * (C11 - C12) * C44 / denom_R if denom_R != 0 else float('nan')
    G = (G_V + G_R) / 2.0

    def safe(fn):
        try:
            v = fn()
            return v if isinstance(v, float) and v == v and abs(v) != float('inf') else float('nan')
        except Exception:
            return float('nan')

    E = safe(lambda: 9 * B * G / (3 * B + G))
    nu = safe(lambda: (3 * B - 2 * G) / (2 * (3 * B + G)))
    B_G_ratio = safe(lambda: B / G)
    A = safe(lambda: 2 * C44 / (C11 - C12))
    Hv = safe(lambda: 2 * ((G / B) ** 2 * G) ** 0.585 - 3) if G > 0 and B > 0 else float('nan')
    return {
        'B': B, 'G_V': G_V, 'G_R': G_R, 'G_VRH': G,
        'E': E, 'nu': nu, 'B_G_ratio': B_G_ratio,
        'Cauchy': Cauchy, 'A': A, 'Hv': Hv,
    }


def parse_elastic_output(output):
    result = {}
    patterns = {
        'B': r'B\(GPa\)\s*=\s*([\d.]+)',
        'C11': r'c11\(GPa\)\s*=\s*([\d.]+)',
        'C12': r'c12\(GPa\)\s*=\s*([\d.]+)',
        'C44': r'c44\(GPa\)\s*=\s*([\d.]+)',
        'cprime': r"c'\(GPa\)\s*=\s*([\d.]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, output)
        if match:
            result[key] = float(match.group(1))
    return result


def _fit_once(eos, xk, yk):
    old = sys.stdout
    sys.stdout = StringIO()
    try:
        popt, rsq = eos.distortion_fit(xk, yk, title='')
    except Exception:
        return None
    finally:
        sys.stdout = old
    a0 = popt[1] if len(popt) > 1 else yk[0]
    resid = np.abs(yk - (popt[0] * xk ** 2 + a0))
    return popt[0], rsq, resid


def _robust_distortion_fit(eos, deltas, energies):
    """Fit E = a2*delta^2 + a0 to a volume-conserving distortion, dropping the
    points that converged to a spurious electronic state.

    Step 1 -- absolute gross-outlier removal: a real distortion energy is
    < ~0.01 Ry over delta<=0.05, so any point sitting more than
    ELASTIC_OUTLIER_GAP_RY above the curve minimum is a spurious basin flip.
    Step 2 -- statistical-outlier removal: iteratively drop a point whose
    residual dwarfs its peers (> FACTOR x median peer residual AND above an
    absolute floor), which catches moderate mis-convergence without touching a
    genuinely flat parabola.

    The remaining fit is accepted UNCONDITIONALLY as long as >= ELASTIC_MIN_PTS
    points survive: a low R^2 usually just means c'~0 (a near-Bain-instability
    soft alloy whose orthorhombic well is intrinsically flat), and that small or
    negative c' is the real, physical answer -- exactly the stage2 lesson that
    R^2 must not gate shallow wells. R^2 is returned as a diagnostic only.
    Returns (a2_coeff, rsq, n_kept, n_dropped) or None (too few points).
    """
    x = np.asarray(deltas, dtype=float)
    y = np.asarray(energies, dtype=float)

    # Step 1: absolute gross-outlier removal.
    keep = (y - y.min()) <= ELASTIC_OUTLIER_GAP_RY
    if keep.sum() < ELASTIC_MIN_PTS:
        return None

    # Step 2: iterative statistical-outlier removal.
    while keep.sum() > ELASTIC_MIN_PTS:
        fit = _fit_once(eos, x[keep], y[keep])
        if fit is None:
            return None
        _, _, resid = fit
        worst_local = int(np.argmax(resid))
        peers = np.delete(resid, worst_local)
        med = np.median(peers)
        if (resid[worst_local] > ELASTIC_OUTLIER_FACTOR * med
                and resid[worst_local] > ELASTIC_OUTLIER_FLOOR_RY):
            keep[np.where(keep)[0][worst_local]] = False
        else:
            break

    fit = _fit_once(eos, x[keep], y[keep])
    if fit is None:
        return None
    a2, rsq, _ = fit
    return a2, rsq, int(keep.sum()), int((~keep).sum())


def fit_elastic(alloy_id, sws0, B0, stage_dir):
    """Compute cubic elastic constants with an outlier guard on the 6 distortion
    points of each mode. Reimplements pyemto's cubic branch so we can drop
    spurious-basin points before the parabola fit and so a negative c' (a
    Born-unstable BCC) is reported rather than silently dropped by a
    positive-number regex. Returns a dict with C11/C12/C44/cprime and the two
    fit R^2, or None when a mode cannot be salvaged (needs recompute).
    """
    from pyemto.EOS.EOS import EOS

    folder = os.path.join(stage_dir, alloy_id)
    system = pyemto.System(folder=folder)
    system.bulk(
        jobname=alloy_id,
        sws=sws0,
        atoms=['Fe'],  # placeholder
        **EMTO_PARAMS,
    )
    system.bmod = B0
    system.sws = sws0

    if system.lat != 'bcc':
        return None  # this reimplementation covers the bcc pipeline only

    eos = EOS(name=system.jobname, xc=system.xc, method='morse', units='bohr')
    deltas = system.elastic_constants_deltas

    def gather(dist_tags):
        xs, ys = [], []
        for i, tag in enumerate(dist_tags):
            job = system.create_jobname(system.jobname + tag)
            old = sys.stdout
            sys.stdout = StringIO()
            try:
                en = system.get_energy(job, folder=system.folder, func=system.xc)
            except Exception:
                en = None
            finally:
                sys.stdout = old
            if en is not None:
                xs.append(deltas[i])
                ys.append(en)
        return xs, ys

    xo, yo = gather(['_bcco0', '_bcco1', '_bcco2', '_bcco3', '_bcco4', '_bcco5'])
    xm, ym = gather(['_bccm0', '_bccm1', '_bccm2', '_bccm3', '_bccm4', '_bccm5'])
    if len(yo) < ELASTIC_MIN_PTS or len(ym) < ELASTIC_MIN_PTS:
        return None

    fit_cp = _robust_distortion_fit(eos, xo, yo)
    fit_c44 = _robust_distortion_fit(eos, xm, ym)
    if fit_cp is None or fit_c44 is None:
        return None

    volume = 4.0 / 3.0 * np.pi * system.sws ** 3
    cprime = fit_cp[0] / 2.0 / volume * system.RyBohr3_to_GPa
    c44 = fit_c44[0] / 2.0 / volume * system.RyBohr3_to_GPa
    c11 = system.bmod + 4.0 / 3.0 * cprime
    c12 = system.bmod - 2.0 / 3.0 * cprime

    return {
        'C11': c11, 'C12': c12, 'C44': c44, 'cprime': cprime,
        'R2_cprime': fit_cp[1], 'R2_c44': fit_c44[1],
        'n_drop_cprime': fit_cp[3], 'n_drop_c44': fit_c44[3],
    }


def analyze_all(result_csv_path, error_csv_path, stage2_csv_path, stage_dir):
    os.makedirs(os.path.dirname(result_csv_path), exist_ok=True)

    # Load stage2 results for SWS0 and B0
    stage2_data = {}
    with open(stage2_csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stage2_data[row['DFT_ID']] = {
                'alloy': row['Alloy'],
                'sws0': float(row['SWS0']),
                'B0': float(row['B0']),
            }

    # Load existing results to skip
    existing = set()
    if os.path.isfile(result_csv_path):
        with open(result_csv_path, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing.add(row['DFT_ID'])

    n_success = 0
    n_error = 0
    header = ['DFT_ID', 'Alloy', 'SWS0', 'B0', 'C11', 'C12', 'C44', 'cprime',
              'B', 'G_V', 'G_R', 'G_VRH', 'E', 'nu', 'B_G_ratio',
              'Cauchy', 'A', 'Hv', 'R2_cprime', 'R2_c44',
              'n_drop_cprime', 'n_drop_c44', 'born_stable']

    def fmt(v, nd):
        # blank for NaN/inf so downstream reads them as missing, not garbage
        try:
            if not (isinstance(v, float) and v == v and abs(v) != float('inf')):
                return ''
        except Exception:
            return ''
        return f"{v:.{nd}f}"

    for alloy_id, data in stage2_data.items():
        if alloy_id in existing:
            n_success += 1
            continue

        errors = check_emto_errors(alloy_id, stage_dir)
        if errors:
            write_error_report(alloy_id, data['alloy'], errors, error_csv_path)
            n_error += len(errors)

        result = fit_elastic(alloy_id, data['sws0'], data['B0'], stage_dir)
        if result is None:
            n_error += 1
            continue

        props = calc_mechanical_properties(result['C11'], result['C12'], result['C44'])
        born_stable = (result['cprime'] > 0 and result['C44'] > 0
                       and result['C11'] + 2 * result['C12'] > 0)

        file_exists = os.path.isfile(result_csv_path)
        with open(result_csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(header)
            writer.writerow([
                alloy_id, data['alloy'],
                f"{data['sws0']:.6f}", f"{data['B0']:.2f}",
                fmt(result['C11'], 2), fmt(result['C12'], 2), fmt(result['C44'], 2),
                fmt(result['cprime'], 2),
                fmt(props['B'], 2), fmt(props['G_V'], 2), fmt(props['G_R'], 2),
                fmt(props['G_VRH'], 2), fmt(props['E'], 2), fmt(props['nu'], 4),
                fmt(props['B_G_ratio'], 4), fmt(props['Cauchy'], 2),
                fmt(props['A'], 4), fmt(props['Hv'], 2),
                fmt(result['R2_cprime'], 6), fmt(result['R2_c44'], 6),
                result['n_drop_cprime'], result['n_drop_c44'],
                'Y' if born_stable else 'N',
            ])
        n_success += 1

    print(f"\nElastic analysis complete: {n_success} succeeded, {n_error} errors")
