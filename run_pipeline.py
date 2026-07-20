import os
import sys
import csv
import argparse
import numpy as np
from config import (CSV_FILE, STAGE_DIRS, RESULTS_DIR, ELEMENTS,
                    COARSE_N_POINTS, COARSE_RANGE, FINE_N_POINTS, FINE_RANGE,
                    DEFAULT_LATPATH)
from vegard import calc_vegard_sws
from emto_generator import parse_csv, generate_eos_inputs, generate_elastic_inputs
from eos_analysis import analyze_all as eos_analyze_all
from elastic_analysis import analyze_all as elastic_analyze_all
from error_collector import summarize_errors


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='High-throughput EMTO pipeline for BCC RHEA')
    parser.add_argument('--stage', type=int, choices=[1, 2, 3])
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--analyze', action='store_true')
    parser.add_argument('--retry', action='store_true')
    parser.add_argument('--errors', action='store_true')
    parser.add_argument('--latpath', type=str, default=DEFAULT_LATPATH)
    return parser.parse_args(argv)


def _make_sws_list(center, n_points, sws_range):
    return list(np.linspace(center * (1 - sws_range),
                            center * (1 + sws_range),
                            n_points))


def _result_path(filename):
    return os.path.join(RESULTS_DIR, filename)


def stage1_generate(alloys, latpath):
    stage_dir = STAGE_DIRS[1]
    n_generated = 0
    n_skipped = 0
    for alloy in alloys:
        alloy_dir = os.path.join(stage_dir, alloy['id'])
        if os.path.isdir(alloy_dir):
            n_skipped += 1
            continue
        sws_guess = calc_vegard_sws(alloy['composition'])
        sws_list = _make_sws_list(sws_guess, COARSE_N_POINTS, COARSE_RANGE)
        generate_eos_inputs(alloy['id'], alloy['atoms'], alloy['concs'],
                            sws_list, stage_dir, latpath)
        n_generated += 1
    print(f"Stage 1 generate: {n_generated} generated, {n_skipped} skipped (already exist)")


def stage1_analyze(alloys):
    eos_analyze_all(
        stage=1,
        result_csv_path=_result_path('stage1_coarse_results.csv'),
        error_csv_path=_result_path('stage1_errors.csv'),
        retry_csv_path=_result_path('stage1_retry_queue.csv'),
        alloys=alloys,
    )


def stage1_retry(alloys, latpath):
    retry_path = _result_path('stage1_retry_queue.csv')
    if not os.path.isfile(retry_path):
        print("No retry queue found.")
        return

    retry_entries = {}
    with open(retry_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            retry_entries[row['DFT_ID']] = float(row['new_sws_center'])

    # Check which have already succeeded
    existing = set()
    result_path = _result_path('stage1_coarse_results.csv')
    if os.path.isfile(result_path):
        with open(result_path, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing.add(row['DFT_ID'])

    alloy_lookup = {a['id']: a for a in alloys}
    n_generated = 0

    for alloy_id, new_center in retry_entries.items():
        if alloy_id in existing:
            continue
        alloy = alloy_lookup.get(alloy_id)
        if alloy is None:
            continue
        sws_list = _make_sws_list(new_center, COARSE_N_POINTS, COARSE_RANGE)
        generate_eos_inputs(alloy['id'], alloy['atoms'], alloy['concs'],
                            sws_list, STAGE_DIRS[1], latpath)
        n_generated += 1

    print(f"Stage 1 retry: {n_generated} re-generated with shifted SWS centers")


def stage2_generate(alloys, latpath):
    stage1_results = _result_path('stage1_coarse_results.csv')
    if not os.path.isfile(stage1_results):
        sys.exit("Error: stage1 results not found. Run --stage 1 --analyze first.")

    sws0_map = {}
    with open(stage1_results, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sws0_map[row['DFT_ID']] = float(row['SWS0'])

    stage_dir = STAGE_DIRS[2]
    n_generated = 0
    n_skipped = 0

    for alloy in alloys:
        if alloy['id'] not in sws0_map:
            continue
        alloy_dir = os.path.join(stage_dir, alloy['id'])
        if os.path.isdir(alloy_dir):
            n_skipped += 1
            continue
        sws0 = sws0_map[alloy['id']]
        sws_list = _make_sws_list(sws0, FINE_N_POINTS, FINE_RANGE)
        generate_eos_inputs(alloy['id'], alloy['atoms'], alloy['concs'],
                            sws_list, stage_dir, latpath)
        n_generated += 1

    print(f"Stage 2 generate: {n_generated} generated, {n_skipped} skipped")


def stage2_analyze(alloys):
    eos_analyze_all(
        stage=2,
        result_csv_path=_result_path('stage2_fine_results.csv'),
        error_csv_path=_result_path('stage2_errors.csv'),
        retry_csv_path=None,
        alloys=alloys,
    )


def stage3_generate(alloys, latpath):
    stage2_results = _result_path('stage2_fine_results.csv')
    if not os.path.isfile(stage2_results):
        sys.exit("Error: stage2 results not found. Run --stage 2 --analyze first.")

    sws0_map = {}
    with open(stage2_results, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sws0_map[row['DFT_ID']] = float(row['SWS0'])

    stage_dir = STAGE_DIRS[3]
    n_generated = 0
    n_skipped = 0

    for alloy in alloys:
        if alloy['id'] not in sws0_map:
            continue
        alloy_dir = os.path.join(stage_dir, alloy['id'])
        if os.path.isdir(alloy_dir):
            n_skipped += 1
            continue
        sws0 = sws0_map[alloy['id']]
        generate_elastic_inputs(alloy['id'], alloy['atoms'], alloy['concs'],
                                sws0, stage_dir, latpath)
        n_generated += 1

    print(f"Stage 3 generate: {n_generated} generated, {n_skipped} skipped")


def stage3_analyze():
    elastic_analyze_all(
        result_csv_path=_result_path('final_mechanical_properties.csv'),
        error_csv_path=_result_path('stage3_errors.csv'),
        stage2_csv_path=_result_path('stage2_fine_results.csv'),
        stage_dir=STAGE_DIRS[3],
    )


def show_errors(stage=None):
    if stage is None:
        for s in [1, 2, 3]:
            error_file = _result_path(f'stage{s}_errors.csv')
            if os.path.isfile(error_file):
                print(f"\n=== Stage {s} ===")
                summarize_errors(error_file)
    else:
        error_file = _result_path(f'stage{stage}_errors.csv')
        summarize_errors(error_file)


def main():
    args = parse_args()
    alloys = parse_csv(CSV_FILE)

    if args.errors:
        show_errors(args.stage)
        return

    if args.stage is None:
        sys.exit("Error: --stage is required (unless using --errors)")

    if args.generate:
        if args.stage == 1:
            stage1_generate(alloys, args.latpath)
        elif args.stage == 2:
            stage2_generate(alloys, args.latpath)
        elif args.stage == 3:
            stage3_generate(alloys, args.latpath)

    elif args.analyze:
        if args.stage == 1:
            stage1_analyze(alloys)
        elif args.stage == 2:
            stage2_analyze(alloys)
        elif args.stage == 3:
            stage3_analyze()

    elif args.retry:
        if args.stage == 1:
            stage1_retry(alloys, args.latpath)
        else:
            print("Retry is only supported for stage 1")


if __name__ == '__main__':
    main()
