import os
import csv
import re
import sys
from io import StringIO
import numpy as np
import pyemto
from config import EMTO_PARAMS
from error_collector import check_emto_errors, write_error_report


def calc_mechanical_properties(C11, C12, C44):
    B = (C11 + 2 * C12) / 3.0
    G_V = (C11 - C12 + 3 * C44) / 5.0
    G_R = 5 * (C11 - C12) * C44 / (4 * C44 + 3 * (C11 - C12))
    G = (G_V + G_R) / 2.0
    E = 9 * B * G / (3 * B + G)
    nu = (3 * B - 2 * G) / (2 * (3 * B + G))
    B_G_ratio = B / G
    Cauchy = C12 - C44
    A = 2 * C44 / (C11 - C12)
    k = G / B
    Hv = 2 * (k**2 * G)**0.585 - 3
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


def fit_elastic(alloy_id, sws0, B0, stage_dir):
    folder = os.path.join(stage_dir, alloy_id)
    system = pyemto.System(folder=folder)
    system.bulk(
        jobname=alloy_id,
        sws=sws0,
        atoms=['Fe'],  # placeholder
        **EMTO_PARAMS,
    )
    system.bmod = B0

    # Capture stdout from elastic_constants_analyze
    old_stdout = sys.stdout
    sys.stdout = captured = StringIO()
    try:
        system.elastic_constants_analyze(sws=sws0, bmod=B0)
    except SystemExit:
        sys.stdout = old_stdout
        return None
    except Exception:
        sys.stdout = old_stdout
        return None
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    result = parse_elastic_output(output)

    if 'C11' not in result or 'C12' not in result or 'C44' not in result:
        return None

    return result


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
    header = ['DFT_ID', 'Alloy', 'SWS0', 'B0', 'C11', 'C12', 'C44',
              'B', 'G_V', 'G_R', 'G_VRH', 'E', 'nu', 'B_G_ratio',
              'Cauchy', 'A', 'Hv']

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

        file_exists = os.path.isfile(result_csv_path)
        with open(result_csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(header)
            writer.writerow([
                alloy_id, data['alloy'],
                f"{data['sws0']:.6f}", f"{data['B0']:.2f}",
                f"{result['C11']:.2f}", f"{result['C12']:.2f}", f"{result['C44']:.2f}",
                f"{props['B']:.2f}", f"{props['G_V']:.2f}", f"{props['G_R']:.2f}",
                f"{props['G_VRH']:.2f}", f"{props['E']:.2f}", f"{props['nu']:.4f}",
                f"{props['B_G_ratio']:.4f}", f"{props['Cauchy']:.2f}",
                f"{props['A']:.4f}", f"{props['Hv']:.2f}",
            ])
        n_success += 1

    print(f"\nElastic analysis complete: {n_success} succeeded, {n_error} errors")
