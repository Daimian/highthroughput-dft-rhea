# High-Throughput EMTO Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python pipeline that generates EMTO KGRN/KFCD input files for ~1600 BCC refractory HEA compositions, fits equations of state in two passes (coarse then fine), and computes elastic constants and mechanical properties.

**Architecture:** Six Python modules — `config.py` (constants), `vegard.py` (initial SWS guess), `emto_generator.py` (pyemto input generation), `error_collector.py` (EMTO error scanning), `eos_analysis.py` (EOS fitting with retry logic), `elastic_analysis.py` (elastic constants + mechanical properties) — orchestrated by a CLI entry point `run_pipeline.py` with `--stage`, `--generate`/`--analyze`/`--retry`/`--errors` flags.

**Tech Stack:** Python 3, pyemto 0.9.5, numpy, csv (stdlib), argparse (stdlib)

## Global Constraints

- All EMTO calculations use: `lat='bcc'`, `xc='PBE'`, `afm='P'`, `expan='S'`, `sofc='Y'`
- CSV concentrations are in atomic percent (sum to 100); pyemto expects fractions (sum to 1.0) for `concs`
- pyemto's `elastic_constants_analyze()` returns None and only prints results — we must capture stdout and parse, or reimplement the calculation from `get_energy()` + distortion fit
- pyemto's `lattice_constants_analyze()` returns `(sws0, B0, e0, grun)` for cubic systems
- Jobnames follow pyemto convention: `prefix_SWS.SSSSSS` (e.g., `DFT_0001_2.940000`)
- KSTR/BMDL/SHAPE files are user-provided via `--latpath`; this codebase never generates them
- All file paths in the project are relative to the project root

---

### Task 1: config.py and vegard.py

**Files:**
- Create: `config.py`
- Create: `vegard.py`
- Create: `tests/test_vegard.py`

**Interfaces:**
- Produces:
  - `config.ELEMENT_SWS: dict[str, float]` — BCC SWS in Bohr for 9 elements
  - `config.ELEMENTS: list[str]` — ordered element list
  - `config.EMTO_PARAMS: dict` — shared EMTO kwargs
  - `config.CSV_FILE: str`, `config.STAGE_DIRS: dict`, `config.RESULTS_DIR: str`
  - `config.COARSE_N_POINTS: int`, `config.COARSE_RANGE: float`, `config.FINE_N_POINTS: int`, `config.FINE_RANGE: float`
  - `vegard.calc_vegard_sws(composition: dict) -> float`

- [ ] **Step 1: Write test for vegard**

```python
# tests/test_vegard.py
import pytest
from vegard import calc_vegard_sws

def test_pure_element():
    assert calc_vegard_sws({'W': 100}) == pytest.approx(2.95)

def test_binary_equal():
    expected = 0.5 * 2.95 + 0.5 * 2.88  # W50Re50
    assert calc_vegard_sws({'W': 50, 'Re': 50}) == pytest.approx(expected)

def test_quinary():
    comp = {'Ti': 20, 'Nb': 20, 'Ta': 20, 'Mo': 20, 'W': 20}
    expected = 0.2 * (3.05 + 3.07 + 3.07 + 2.93 + 2.95)
    assert calc_vegard_sws(comp) == pytest.approx(expected)

def test_actual_csv_row():
    # DFT_0010: Nb5Ta45Mo5W45
    comp = {'Nb': 5, 'Ta': 45, 'Mo': 5, 'W': 45}
    expected = 0.05*3.07 + 0.45*3.07 + 0.05*2.93 + 0.45*2.95
    assert calc_vegard_sws(comp) == pytest.approx(expected)

def test_empty_raises():
    with pytest.raises(ValueError):
        calc_vegard_sws({})

def test_bad_sum_raises():
    with pytest.raises(ValueError):
        calc_vegard_sws({'W': 50})  # doesn't sum to 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_vegard.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'vegard'`

- [ ] **Step 3: Write config.py**

```python
# config.py
ELEMENT_SWS = {
    'Ti': 3.05, 'Zr': 3.35, 'Hf': 3.31,
    'V': 2.82, 'Nb': 3.07, 'Ta': 3.07,
    'Mo': 2.93, 'W': 2.95, 'Re': 2.88,
}

ELEMENTS = ['Ti', 'Zr', 'Hf', 'V', 'Nb', 'Ta', 'Mo', 'W', 'Re']

EMTO_PARAMS = dict(
    lat='bcc',
    xc='PBE',
    afm='P',
    expan='S',
    sofc='Y',
)

CSV_FILE = '20260718-refractory-hea-compositions-1600-highthroughput-dft.csv'

STAGE_DIRS = {
    1: 'stage1_eos_coarse',
    2: 'stage2_eos_fine',
    3: 'stage3_elastic',
}

RESULTS_DIR = 'results'

COARSE_N_POINTS = 6
COARSE_RANGE = 0.03

FINE_N_POINTS = 11
FINE_RANGE = 0.015
```

- [ ] **Step 4: Write vegard.py**

```python
# vegard.py
from config import ELEMENT_SWS

def calc_vegard_sws(composition):
    if not composition:
        raise ValueError("composition must not be empty")
    total = sum(composition.values())
    if abs(total - 100.0) > 0.5:
        raise ValueError(f"concentrations sum to {total}, expected 100")
    sws = 0.0
    for elem, conc in composition.items():
        sws += (conc / 100.0) * ELEMENT_SWS[elem]
    return sws
```

- [ ] **Step 5: Run tests**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_vegard.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add config.py vegard.py tests/test_vegard.py
git commit -m "feat: add config constants and Vegard's law SWS calculator"
```

---

### Task 2: emto_generator.py — CSV parsing and EOS input generation

**Files:**
- Create: `emto_generator.py`
- Create: `tests/test_emto_generator.py`

**Interfaces:**
- Consumes: `config.ELEMENTS`, `config.EMTO_PARAMS`, `config.CSV_FILE`
- Produces:
  - `parse_csv(csv_path: str) -> list[dict]` — returns `[{'id': 'DFT_0001', 'alloy': 'W91Re9', 'atoms': ['W','Re'], 'concs': [91, 9], 'composition': {'W': 91, 'Re': 9}}]`
  - `generate_eos_inputs(alloy_id: str, atoms: list[str], concs: list[int], sws_list: list[float], stage_dir: str, latpath: str) -> None`
  - `generate_elastic_inputs(alloy_id: str, atoms: list[str], concs: list[int], sws0: float, stage_dir: str, latpath: str) -> None`

- [ ] **Step 1: Write test for parse_csv**

```python
# tests/test_emto_generator.py
import os
import pytest
from emto_generator import parse_csv

def test_parse_csv():
    csv_path = os.path.join(os.path.dirname(__file__), '..',
                            '20260718-refractory-hea-compositions-1600-highthroughput-dft.csv')
    alloys = parse_csv(csv_path)
    assert len(alloys) == 1597

    first = alloys[0]
    assert first['id'] == 'DFT_0001'
    assert first['alloy'] == 'W91Re9'
    assert first['atoms'] == ['W', 'Re']
    assert first['concs'] == [91, 9]
    assert first['composition'] == {'W': 91, 'Re': 9}

    # Check a multi-component alloy
    dft10 = alloys[9]  # DFT_0010
    assert dft10['id'] == 'DFT_0010'
    assert dft10['alloy'] == 'Nb5Ta45Mo5W45'
    assert set(dft10['atoms']) == {'Nb', 'Ta', 'Mo', 'W'}
    assert sum(dft10['concs']) == 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_emto_generator.py::test_parse_csv -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write parse_csv in emto_generator.py**

```python
# emto_generator.py
import os
import csv
import numpy as np
import pyemto
from config import ELEMENTS, EMTO_PARAMS

def parse_csv(csv_path):
    alloys = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            atoms = []
            concs = []
            composition = {}
            for elem in ELEMENTS:
                c = int(row[elem])
                if c > 0:
                    atoms.append(elem)
                    concs.append(c)
                    composition[elem] = c
            alloys.append({
                'id': row['DFT_ID'],
                'alloy': row['Alloy'],
                'atoms': atoms,
                'concs': concs,
                'composition': composition,
            })
    return alloys
```

- [ ] **Step 4: Run parse_csv test**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_emto_generator.py::test_parse_csv -v`
Expected: PASS

- [ ] **Step 5: Write generate_eos_inputs**

Add to `emto_generator.py`:

```python
def generate_eos_inputs(alloy_id, atoms, concs, sws_list, stage_dir, latpath):
    folder = os.path.join(stage_dir, alloy_id)
    os.makedirs(folder, exist_ok=True)

    concs_frac = [c / 100.0 for c in concs]
    splts = [0.0] * len(atoms)

    system = pyemto.System(folder=folder)
    system.bulk(
        jobname=alloy_id,
        latpath=latpath,
        atoms=atoms,
        concs=concs_frac,
        splts=splts,
        sws=sws_list[0],
        **EMTO_PARAMS,
    )
    system.lattice_constants_batch_generate(sws=sws_list)


def generate_elastic_inputs(alloy_id, atoms, concs, sws0, stage_dir, latpath):
    folder = os.path.join(stage_dir, alloy_id)
    os.makedirs(folder, exist_ok=True)

    concs_frac = [c / 100.0 for c in concs]
    splts = [0.0] * len(atoms)

    system = pyemto.System(folder=folder)
    system.bulk(
        jobname=alloy_id,
        latpath=latpath,
        atoms=atoms,
        concs=concs_frac,
        splts=splts,
        sws=sws0,
        **EMTO_PARAMS,
    )
    system.elastic_constants_batch_generate(sws=sws0)
```

- [ ] **Step 6: Write smoke test for generate_eos_inputs**

Add to `tests/test_emto_generator.py`:

```python
import tempfile
import numpy as np
from emto_generator import generate_eos_inputs

def test_generate_eos_inputs_creates_files(tmp_path):
    # This test requires a latpath with bcc structure files.
    # Use a dummy latpath — pyemto will create the folder structure
    # and KGRN/KFCD input files even without actual structure output files.
    latpath = str(tmp_path / "lat")
    os.makedirs(latpath, exist_ok=True)
    stage_dir = str(tmp_path / "stage1")

    sws_list = list(np.linspace(2.85, 3.05, 6))
    generate_eos_inputs(
        alloy_id='DFT_0001',
        atoms=['W', 'Re'],
        concs=[91, 9],
        sws_list=sws_list,
        stage_dir=stage_dir,
        latpath=latpath,
    )

    alloy_dir = os.path.join(stage_dir, 'DFT_0001')
    assert os.path.isdir(alloy_dir)
    # Check KGRN input files were created (one per SWS point)
    kgrn_dir = os.path.join(alloy_dir, 'kgrn')
    assert os.path.isdir(kgrn_dir)
    kgrn_files = [f for f in os.listdir(kgrn_dir) if f.endswith('.dat')]
    assert len(kgrn_files) == 6
```

- [ ] **Step 7: Run all tests**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_emto_generator.py -v`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add emto_generator.py tests/test_emto_generator.py
git commit -m "feat: add CSV parser and EMTO input generation functions"
```

---

### Task 3: error_collector.py

**Files:**
- Create: `error_collector.py`
- Create: `tests/test_error_collector.py`

**Interfaces:**
- Produces:
  - `check_emto_errors(alloy_id: str, stage_dir: str) -> list[dict]` — each dict: `{'sws': float, 'error_type': str, 'message': str}`
  - `write_error_report(alloy_id: str, alloy_name: str, errors: list[dict], error_csv_path: str) -> None`
  - `summarize_errors(error_csv_path: str) -> None`

- [ ] **Step 1: Write tests with mock EMTO output files**

```python
# tests/test_error_collector.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_error_collector.py -v`
Expected: FAIL

- [ ] **Step 3: Implement error_collector.py**

```python
# error_collector.py
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

        if os.path.getsize(kfcd_file) == 0:
            errors.append({'sws': sws, 'error_type': 'missing_output',
                           'message': f'kfcd output empty for {job}'})
            continue

        # Check SCF convergence in KGRN output
        if os.path.isfile(kgrn_file):
            with open(kgrn_file, 'r') as f:
                content = f.read()
            if 'NOT CONVERGED' in content.upper():
                errors.append({'sws': sws, 'error_type': 'scf_not_converged',
                               'message': f'KGRN SCF not converged for {job}'})

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
```

- [ ] **Step 4: Run tests**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_error_collector.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add error_collector.py tests/test_error_collector.py
git commit -m "feat: add EMTO error collector for scanning calculation outputs"
```

---

### Task 4: eos_analysis.py — EOS fitting with retry logic

**Files:**
- Create: `eos_analysis.py`
- Create: `tests/test_eos_analysis.py`

**Interfaces:**
- Consumes:
  - `error_collector.check_emto_errors(alloy_id, stage_dir) -> list[dict]`
  - `error_collector.write_error_report(alloy_id, alloy_name, errors, error_csv_path)`
  - `emto_generator.parse_csv(csv_path) -> list[dict]`
  - `vegard.calc_vegard_sws(composition) -> float`
  - `config.COARSE_RANGE`
- Produces:
  - `fit_eos(alloy_id: str, sws_list: list[float], stage_dir: str) -> tuple[float, float, float, float] | None` — returns `(sws0, B0, e0, grun)` or None
  - `check_coarse_fit(sws0: float, sws_list: list[float]) -> dict | None` — returns `{'new_sws_center': float, 'reason': str}` or None
  - `analyze_all(stage: int, result_csv_path: str, error_csv_path: str, retry_csv_path: str | None, alloys: list[dict]) -> None`

- [ ] **Step 1: Write tests for check_coarse_fit**

```python
# tests/test_eos_analysis.py
import pytest
from eos_analysis import check_coarse_fit

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_eos_analysis.py -v`
Expected: FAIL

- [ ] **Step 3: Implement eos_analysis.py**

```python
# eos_analysis.py
import os
import csv
import numpy as np
import pyemto
from config import EMTO_PARAMS, COARSE_RANGE, RESULTS_DIR
from error_collector import check_emto_errors, write_error_report


def fit_eos(alloy_id, sws_list, stage_dir):
    folder = os.path.join(stage_dir, alloy_id)
    system = pyemto.System(folder=folder)
    system.bulk(
        jobname=alloy_id,
        sws=sws_list[0],
        atoms=['Fe'],  # placeholder, overridden by existing output files
        **EMTO_PARAMS,
    )

    errors = check_emto_errors(alloy_id, stage_dir)
    error_sws = {e['sws'] for e in errors}
    valid_sws = [s for s in sws_list if s not in error_sws]

    if len(valid_sws) < 4:
        return None, errors

    try:
        result = system.lattice_constants_analyze(sws=valid_sws, prn=False)
        sws0, B0, e0, grun = result
    except Exception:
        return None, errors

    if B0 <= 0 or B0 > 1000:
        return None, errors

    return (sws0, B0, e0, grun), errors


def check_coarse_fit(sws0, sws_list):
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


def analyze_all(stage, result_csv_path, error_csv_path, alloys, stage_dir,
                retry_csv_path=None):
    os.makedirs(os.path.dirname(result_csv_path), exist_ok=True)
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

        # Reconstruct sws_list from kgrn files
        sws_list = _get_sws_from_dir(alloy_dir, alloy_id)
        if not sws_list:
            continue

        result, errors = fit_eos(alloy_id, sws_list, stage_dir)

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
```

- [ ] **Step 4: Run tests**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_eos_analysis.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add eos_analysis.py tests/test_eos_analysis.py
git commit -m "feat: add EOS fitting with coarse-fit validation and retry logic"
```

---

### Task 5: elastic_analysis.py — elastic constants and mechanical properties

**Files:**
- Create: `elastic_analysis.py`
- Create: `tests/test_elastic_analysis.py`

**Interfaces:**
- Consumes:
  - `error_collector.check_emto_errors(alloy_id, stage_dir) -> list[dict]`
  - `error_collector.write_error_report(alloy_id, alloy_name, errors, error_csv_path)`
- Produces:
  - `fit_elastic(alloy_id: str, sws0: float, B0: float, stage_dir: str) -> dict | None` — returns `{'C11': float, 'C12': float, 'C44': float, 'cprime': float, ...}` or None
  - `calc_mechanical_properties(C11: float, C12: float, C44: float) -> dict`
  - `analyze_all(result_csv_path: str, error_csv_path: str, stage2_csv_path: str, stage_dir: str) -> None`

Note: pyemto's `elastic_constants_analyze()` returns None and only prints. We must capture stdout and parse the printed output to extract C11, C12, C44, and all polycrystalline averages.

- [ ] **Step 1: Write test for calc_mechanical_properties**

```python
# tests/test_elastic_analysis.py
import pytest
from elastic_analysis import calc_mechanical_properties

def test_mechanical_properties_pure_w():
    # Approximate values for tungsten
    C11, C12, C44 = 523.0, 205.0, 161.0
    props = calc_mechanical_properties(C11, C12, C44)

    B = (C11 + 2 * C12) / 3.0
    assert props['B'] == pytest.approx(B, rel=1e-6)

    G_V = (C11 - C12 + 3 * C44) / 5.0
    G_R = 5 * (C11 - C12) * C44 / (4 * C44 + 3 * (C11 - C12))
    G = (G_V + G_R) / 2.0
    assert props['G_V'] == pytest.approx(G_V, rel=1e-6)
    assert props['G_R'] == pytest.approx(G_R, rel=1e-6)
    assert props['G_VRH'] == pytest.approx(G, rel=1e-6)

    E = 9 * B * G / (3 * B + G)
    assert props['E'] == pytest.approx(E, rel=1e-6)

    nu = (3 * B - 2 * G) / (2 * (3 * B + G))
    assert props['nu'] == pytest.approx(nu, rel=1e-6)

    assert props['B_G_ratio'] == pytest.approx(B / G, rel=1e-6)
    assert props['Cauchy'] == pytest.approx(C12 - C44, rel=1e-6)

    A = 2 * C44 / (C11 - C12)
    assert props['A'] == pytest.approx(A, rel=1e-6)

    k = G / B
    Hv = 2 * (k**2 * G)**0.585 - 3
    assert props['Hv'] == pytest.approx(Hv, rel=1e-6)

def test_mechanical_properties_keys():
    props = calc_mechanical_properties(500, 200, 150)
    expected_keys = {'B', 'G_V', 'G_R', 'G_VRH', 'E', 'nu',
                     'B_G_ratio', 'Cauchy', 'A', 'Hv'}
    assert set(props.keys()) == expected_keys
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_elastic_analysis.py -v`
Expected: FAIL

- [ ] **Step 3: Write test for parsing elastic_constants_analyze stdout**

```python
# Add to tests/test_elastic_analysis.py
from elastic_analysis import parse_elastic_output

def test_parse_elastic_output():
    output = """
***cubic_elastic_constants***

DFT_0001

sws(bohr)      =   2.941
B(GPa)         = 321.30
c11(GPa)       = 523.10
c12(GPa)       = 205.40
c'(GPa)        = 158.85
c44(GPa)       = 161.20
R-squared(c')  = 0.999800
R-squared(c44) = 0.999500

Voigt average:

BV(GPa)  = 311.30
GV(GPa)  = 159.42
EV(GPa)  = 410.50
vV(GPa)  =   0.29

Reuss average:

BR(GPa)  = 311.30
GR(GPa)  = 158.20
ER(GPa)  = 408.30
vR(GPa)  =   0.29

Hill average:

BH(GPa)  = 311.30
GH(GPa)  = 158.81
EH(GPa)  = 409.40
vH(GPa)  =   0.29

Elastic anisotropy:

AVR(GPa)  =   0.00
"""
    result = parse_elastic_output(output)
    assert result['C11'] == pytest.approx(523.10)
    assert result['C12'] == pytest.approx(205.40)
    assert result['C44'] == pytest.approx(161.20)
    assert result['cprime'] == pytest.approx(158.85)
    assert result['B'] == pytest.approx(321.30)
```

- [ ] **Step 4: Implement elastic_analysis.py**

```python
# elastic_analysis.py
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
```

- [ ] **Step 5: Run tests**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_elastic_analysis.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add elastic_analysis.py tests/test_elastic_analysis.py
git commit -m "feat: add elastic constants fitting and mechanical properties calculator"
```

---

### Task 6: run_pipeline.py — CLI entry point

**Files:**
- Create: `run_pipeline.py`
- Create: `tests/test_run_pipeline.py`

**Interfaces:**
- Consumes all modules: `config`, `vegard`, `emto_generator`, `eos_analysis`, `elastic_analysis`, `error_collector`

- [ ] **Step 1: Write test for CLI argument parsing**

```python
# tests/test_run_pipeline.py
import pytest
from run_pipeline import parse_args

def test_stage1_generate():
    args = parse_args(['--stage', '1', '--generate', '--latpath', '/tmp/lat'])
    assert args.stage == 1
    assert args.generate is True
    assert args.analyze is False
    assert args.retry is False
    assert args.latpath == '/tmp/lat'

def test_stage1_analyze():
    args = parse_args(['--stage', '1', '--analyze'])
    assert args.stage == 1
    assert args.analyze is True

def test_stage1_retry():
    args = parse_args(['--stage', '1', '--retry', '--latpath', '/tmp/lat'])
    assert args.retry is True

def test_errors_all_stages():
    args = parse_args(['--errors'])
    assert args.errors is True
    assert args.stage is None

def test_errors_specific_stage():
    args = parse_args(['--errors', '--stage', '2'])
    assert args.errors is True
    assert args.stage == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_run_pipeline.py -v`
Expected: FAIL

- [ ] **Step 3: Implement run_pipeline.py**

```python
# run_pipeline.py
import os
import sys
import csv
import argparse
import numpy as np
from config import (CSV_FILE, STAGE_DIRS, RESULTS_DIR, ELEMENTS,
                    COARSE_N_POINTS, COARSE_RANGE, FINE_N_POINTS, FINE_RANGE)
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
    parser.add_argument('--latpath', type=str, default=None)
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
        alloys=alloys,
        stage_dir=STAGE_DIRS[1],
        retry_csv_path=_result_path('stage1_retry_queue.csv'),
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
        alloys=alloys,
        stage_dir=STAGE_DIRS[2],
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
        if args.latpath is None:
            sys.exit("Error: --latpath is required for --generate")
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
        if args.latpath is None:
            sys.exit("Error: --latpath is required for --retry")
        if args.stage == 1:
            stage1_retry(alloys, args.latpath)
        else:
            print("Retry is only supported for stage 1")


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_run_pipeline.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add run_pipeline.py tests/test_run_pipeline.py
git commit -m "feat: add CLI pipeline entry point with stage/generate/analyze/retry/errors flags"
```

---

### Task 7: Integration test and final cleanup

**Files:**
- Create: `tests/test_integration.py`
- Modify: any files that need adjustments found during integration testing

**Interfaces:**
- Consumes: all modules

- [ ] **Step 1: Write integration test for the full stage 1 generate flow**

```python
# tests/test_integration.py
import os
import pytest
import numpy as np
from config import COARSE_N_POINTS, COARSE_RANGE
from emto_generator import parse_csv
from vegard import calc_vegard_sws

def test_vegard_sws_range_reasonable():
    csv_path = os.path.join(os.path.dirname(__file__), '..',
                            '20260718-refractory-hea-compositions-1600-highthroughput-dft.csv')
    alloys = parse_csv(csv_path)
    for alloy in alloys:
        sws = calc_vegard_sws(alloy['composition'])
        assert 2.5 < sws < 3.5, f"{alloy['id']}: SWS={sws} out of reasonable range"

def test_all_compositions_sum_to_100():
    csv_path = os.path.join(os.path.dirname(__file__), '..',
                            '20260718-refractory-hea-compositions-1600-highthroughput-dft.csv')
    alloys = parse_csv(csv_path)
    for alloy in alloys:
        total = sum(alloy['concs'])
        assert total == 100, f"{alloy['id']}: concs sum to {total}"

def test_sws_list_generation():
    center = 3.0
    sws_list = list(np.linspace(center * (1 - COARSE_RANGE),
                                center * (1 + COARSE_RANGE),
                                COARSE_N_POINTS))
    assert len(sws_list) == 6
    assert sws_list[0] == pytest.approx(center * 0.97)
    assert sws_list[-1] == pytest.approx(center * 1.03)
```

- [ ] **Step 2: Run integration tests**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/test_integration.py -v`
Expected: All PASS

- [ ] **Step 3: Run full test suite**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 4: Verify CLI help text works**

Run: `cd /home/dm/workplace/highthroughput-dft-rhea && python run_pipeline.py --help`
Expected: Usage information printed

- [ ] **Step 5: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for CSV parsing, Vegard range, and SWS generation"
```

- [ ] **Step 6: Push to GitHub**

```bash
git push origin master
```
