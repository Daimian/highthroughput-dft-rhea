# High-Throughput EMTO Calculation Pipeline for BCC Refractory HEAs

## Overview

A Python pipeline using pyemto to generate EMTO (KGRN/KFCD) input files and analyze results for ~1600 BCC refractory high-entropy alloy compositions. The pipeline has three stages: coarse EOS fitting, fine EOS fitting, and elastic constants calculation with mechanical properties derivation.

KSTR, BMDL, and SHAPE files are provided externally by the user. This codebase only handles KGRN/KFCD generation, EOS analysis, elastic constants fitting, and mechanical properties calculation.

## Input Data

- CSV file: `20260718-refractory-hea-compositions-1600-highthroughput-dft.csv`
- 1598 alloy compositions (header + 1598 rows; the file has no trailing newline, so `wc -l` reports 1598)
- 9 elements: Ti, Zr, Hf, V, Nb, Ta, Mo, W, Re
- Concentrations in atomic percent (sum to 100)
- Alloy complexity: 2-7 component systems

## Calculation Parameters

- Structure: BCC (CPA for random alloys)
- XC functional: PBE
- Magnetic state: non-magnetic (afm='P')
- Expansion: single (expan='S')
- Core treatment: soft-core (sofc='Y')
- All other KGRN/KFCD parameters: pyemto defaults (nky, amix, efmix, tole, etc.)

## Directory Structure

```
highthroughput-dft-rhea/
├── 20260718-refractory-hea-compositions-1600-highthroughput-dft.csv
├── config.py
├── vegard.py
├── emto_generator.py
├── eos_analysis.py
├── elastic_analysis.py
├── error_collector.py
├── run_pipeline.py
├── stage1_eos_coarse/
│   ├── DFT_0001/
│   ├── DFT_0002/
│   └── ...
├── stage2_eos_fine/
│   ├── DFT_0001/
│   └── ...
├── stage3_elastic/
│   ├── DFT_0001/
│   └── ...
└── results/
    ├── stage1_coarse_results.csv
    ├── stage1_errors.csv
    ├── stage1_retry_queue.csv
    ├── stage2_fine_results.csv
    ├── stage2_errors.csv
    ├── stage3_errors.csv
    └── final_mechanical_properties.csv
```

## Data Flow

```
CSV (1600 compositions)
    │
    ▼
vegard.py: SWS_guess = Σ (c_i / 100) * SWS_i
    │
    ▼ Stage 1: Coarse EOS (6 points, ±3% around SWS_guess)
emto_generator.py → stage1_eos_coarse/DFT_XXXX/
    → user submits to cluster
    → eos_analysis.py:
        ├─ success → results/stage1_coarse_results.csv (SWS0, B0)
        ├─ EMTO error (SCF not converged, etc.) → results/stage1_errors.csv
        └─ EOS fit bad (minimum outside range / poor fit)
              → WARNING + results/stage1_retry_queue.csv (shifted SWS center)
              → re-generate with shifted SWS → user resubmits → re-analyze
    │
    ▼ Stage 2: Fine EOS (11 points, ±1.5% around coarse SWS0)
emto_generator.py → stage2_eos_fine/DFT_XXXX/
    → user submits to cluster
    → eos_analysis.py:
        ├─ success → results/stage2_fine_results.csv (SWS0, B0)
        └─ errors → results/stage2_errors.csv
    │
    ▼ Stage 3: Elastic Constants
emto_generator.py → stage3_elastic/DFT_XXXX/
    → user submits to cluster
    → elastic_analysis.py:
        ├─ success → results/final_mechanical_properties.csv
        └─ errors → results/stage3_errors.csv
```

## Module Specifications

### config.py

Pure constants, no logic.

```python
ELEMENT_SWS = {
    'Ti': 3.05, 'Zr': 3.35, 'Hf': 3.31,
    'V': 2.82, 'Nb': 3.07, 'Ta': 3.07,
    'Mo': 2.93, 'W': 2.95, 'Re': 2.88
}

ELEMENTS = ['Ti', 'Zr', 'Hf', 'V', 'Nb', 'Ta', 'Mo', 'W', 'Re']

EMTO_PARAMS = dict(
    lat='bcc', xc='PBE', afm='P',
    expan='S', sofc='Y'
)

CSV_FILE = '20260718-refractory-hea-compositions-1600-highthroughput-dft.csv'

STAGE_DIRS = {
    1: 'stage1_eos_coarse',
    2: 'stage2_eos_fine',
    3: 'stage3_elastic',
}

RESULTS_DIR = 'results'

COARSE_N_POINTS = 6
COARSE_RANGE = 0.03      # ±3%
FINE_N_POINTS = 11
FINE_RANGE = 0.015        # ±1.5%
```

### vegard.py

Single function:

- `calc_vegard_sws(composition: dict) -> float`
  - Input: `{'Ti': 40, 'Zr': 10, 'Mo': 24, 'W': 26}` (atomic percent, non-zero elements only)
  - Output: weighted average SWS in Bohr
  - Formula: `SWS = Σ (c_i / 100) * ELEMENT_SWS[element_i]`

### emto_generator.py

Three functions, all write KGRN/KFCD files to disk:

- `generate_eos_inputs(alloy_id, atoms, concs, sws_list, stage_dir, latpath)`
  - For each SWS in sws_list: call `System.bulk()` with BCC CPA setup, then `write_input_file()` for KGRN and KFCD
  - CPA setup: single BCC site, all non-zero elements on the same site, concentrations normalized to fractions (divide by 100)
  - Writes to `stage_dir/alloy_id/`

- `generate_elastic_inputs(alloy_id, atoms, concs, sws0, stage_dir, latpath)`
  - Call `System.bulk()` then `elastic_constants_batch_generate(sws=sws0)`
  - Writes to `stage_dir/alloy_id/`

- `parse_csv(csv_path) -> list[dict]`
  - Returns list of `{'id': 'DFT_0001', 'alloy': 'W91Re9', 'atoms': ['W','Re'], 'concs': [91,9]}` for all rows

### error_collector.py

Collects and categorizes errors from EMTO output files across all stages.

- `check_emto_errors(alloy_id, stage_dir) -> list[dict]`
  - Scans KGRN/KFCD output files for known error patterns:
    - SCF not converged
    - Negative DOS at Fermi level
    - KGRN/KFCD crashed (missing or truncated output)
    - NaN or unreasonable energy values
  - Returns list of `{'sws': float, 'error_type': str, 'message': str}`

- `write_error_report(errors: list[dict], error_csv_path)`
  - Appends to stage error CSV: `DFT_ID, Alloy, SWS, error_type, message`

- `summarize_errors(error_csv_path)`
  - Prints summary: count by error_type, list of affected DFT_IDs

### eos_analysis.py

- `fit_eos(alloy_id, sws_list, stage_dir) -> (sws0, B0) | None`
  - First calls `error_collector.check_emto_errors()` to identify failed SWS points
  - Excludes failed points from fitting; if too few valid points remain (< 4), returns None
  - Uses pyemto's `lattice_constants_analyze(sws=valid_sws_list)` to fit Morse EOS
  - Validates the fit result:
    - SWS0 must be within the sampled range (not extrapolated)
    - B0 must be positive and physically reasonable (10-600 GPa for RHEA)
  - If fit is bad: returns None (flagged for retry)

- `check_coarse_fit(alloy_id, sws0, sws_list, vegard_sws) -> dict | None`
  - Checks if the coarse EOS minimum is trustworthy:
    - SWS0 at the edge of the sampled range (< 0.5% from boundary) → bad
    - SWS0 outside the sampled range → bad
  - Returns `{'alloy_id': ..., 'new_sws_center': shifted_value, 'reason': ...}` for retry, or None if OK
  - Shift strategy: move SWS center toward the detected minimum direction by half the range

- `analyze_all(stage, result_csv_path, error_csv_path, retry_csv_path=None)`
  - Iterates all DFT_IDs in the stage directory
  - For each ID:
    - Skip if already in results CSV (resume support)
    - Check for EMTO errors → write to error CSV
    - Attempt EOS fit
    - If fit fails or minimum at edge → write to retry_queue CSV (stage 1 only)
    - If fit succeeds → write to results CSV
  - Prints summary at the end: N succeeded, N errors, N need retry

### elastic_analysis.py

- `fit_elastic(alloy_id, sws0, B0, stage_dir) -> (C11, C12, C44)`
  - Uses pyemto's `elastic_constants_analyze(sws=sws0, bmod=B0)`

- `calc_mechanical_properties(C11, C12, C44) -> dict`
  - B = (C11 + 2*C12) / 3
  - G_V = (C11 - C12 + 3*C44) / 5
  - G_R = 5*(C11-C12)*C44 / (4*C44 + 3*(C11-C12))
  - G = (G_V + G_R) / 2  (Hill average)
  - E = 9*B*G / (3*B + G)
  - v = (3*B - 2*G) / (2*(3*B + G))
  - B/G ratio
  - Cauchy pressure = C12 - C44
  - Zener anisotropy A = 2*C44 / (C11 - C12)
  - Hv = 2*(k^2 * G)^0.585 - 3, where k = G/B (Chen-Niu model)
  - If pyemto's analyze already returns some of these, use those values directly

- `analyze_all(result_csv_path)`
  - Iterates all DFT_IDs, computes all properties
  - Writes `final_mechanical_properties.csv`: DFT_ID, Alloy, SWS0, B0, C11, C12, C44, B, G, E, v, B_G_ratio, Cauchy, A, Hv

### run_pipeline.py

CLI entry point with `--stage`, `--generate`/`--analyze`, and `--retry` flags:

```
python run_pipeline.py --stage 1 --generate [--latpath /path/to/structures]
python run_pipeline.py --stage 1 --analyze
python run_pipeline.py --stage 1 --retry        # re-generate for retry queue, then user resubmits
python run_pipeline.py --stage 1 --analyze       # re-analyze including retried IDs
python run_pipeline.py --stage 2 --generate
python run_pipeline.py --stage 2 --analyze
python run_pipeline.py --stage 3 --generate
python run_pipeline.py --stage 3 --analyze
python run_pipeline.py --errors [--stage N]      # print error summary for stage N or all stages
```

Logic:
- Stage 1 generate: read CSV → vegard SWS → 6-point SWS list → generate inputs
- Stage 1 analyze: fit coarse EOS → results/errors/retry_queue CSVs
- Stage 1 retry: read retry_queue CSV → re-generate inputs with shifted SWS center → user resubmits
- Stage 1 re-analyze: picks up retried IDs, merges into results (can retry multiple rounds)
- Stage 2 generate: read stage1 results → 11-point SWS list around coarse SWS0 → generate inputs
- Stage 2 analyze: fit fine EOS → write stage2_fine_results.csv + stage2_errors.csv
- Stage 3 generate: read stage2 results → generate elastic distortion inputs
- Stage 3 analyze: fit elastic constants → calc properties → final CSV + stage3_errors.csv

Resume support: each generate/analyze step skips DFT_IDs whose output already exists in the results CSV. The retry mechanism appends to the retry queue and clears entries once they succeed on re-analysis.

## Intermediate Result Files

### results/stage1_coarse_results.csv
```
DFT_ID,Alloy,SWS0,B0
DFT_0001,W91Re9,2.943,320.5
...
```

### results/stage1_errors.csv
```
DFT_ID,Alloy,SWS,error_type,message
DFT_0042,Ti40Zr30Hf4Mo26,3.15,scf_not_converged,KGRN did not converge after 100 iterations
...
```

### results/stage1_retry_queue.csv
```
DFT_ID,Alloy,old_sws_center,new_sws_center,reason,retry_round
DFT_0099,V18Nb41Ta41,2.98,3.05,minimum_at_upper_edge,1
...
```

### results/stage2_fine_results.csv
```
DFT_ID,Alloy,SWS0,B0
DFT_0001,W91Re9,2.9418,321.3
...
```

### results/stage2_errors.csv, results/stage3_errors.csv
Same format as stage1_errors.csv.

### results/final_mechanical_properties.csv
```
DFT_ID,Alloy,SWS0,B0,C11,C12,C44,B,G_V,G_R,G_VRH,E,nu,B_G_ratio,Cauchy,A,Hv
DFT_0001,W91Re9,2.9418,321.3,523.1,204.4,163.2,...
...
```

## Out of Scope

- KSTR, BMDL, SHAPE file generation (user-provided)
- Batch job submission to HPC clusters (user handles manually)
- latpath configuration (user provides via CLI argument)
