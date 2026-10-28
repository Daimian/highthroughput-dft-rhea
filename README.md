# highthroughput-dft-rhea

English | [中文](README.zh.md)

A high-throughput EMTO-CPA workflow for BCC refractory high-entropy alloys (RHEAs).
It uses [pyemto](https://github.com/hpleva/pyemto) to generate KGRN/KFCD input files in
bulk, and analyses the cluster output through equation-of-state (EOS) fitting, elastic-constant
fitting, and derivation of mechanical properties.

The input data is `20260718-refractory-hea-compositions-1600-highthroughput-dft.csv`,
containing 1598 compositions (a nine-element system of Ti, Zr, Hf, V, Nb, Ta, Mo, W, Re;
2–7 components; atomic percentages summing to 100).

> **Note**: KSTR / BMDL / SHAPE structure files are supplied by the user (the directory
> pointed to by `--latpath`, default
> `/work/scratch/md88vyxi/workplace/highthroughput-dft-rhea/structures`). This repository
> handles KGRN/KFCD input generation, submission to Slurm (`jobs/`, see the "Cluster
> submission" section), and result analysis.
>
> The `structures/` directory in this repository only tracks the kstr/bmdl/shape **input
> cards** (`*.kstr` / `*.bmdl` / `*.shape`) and the generation script `get_kstr.sh`. The files
> that KGRN and KFCD actually read — `kstr/*.tfh`, `bmdl/*.mdl` and `shape/*.shp` (about
> 280 MB) — are not under version control. After cloning, run `get_kstr.sh` inside
> `structures/` (i.e. `kstr < X.kstr`, `bmdl < X.bmdl`, `shape < X.shape`) to regenerate them.

## Results and status

**The pipeline has run over the full library: stage1 / stage2 / stage3 are all 1598 / 1598 = 100%.**

- `results/final_mechanical_properties.csv` — C11/C12/C44/C′ plus derived mechanical
  quantities, fit quality (R², number of outliers dropped) and Born stability for all 1598
  alloys, **all ground-state confirmed**.
- `results/20260723-refractory-hea-elastic-mechanical-properties-groundstate-confirmed-1598-highthroughput-dft.csv`
  + `results/README-elastic-mechanical-properties.md` — the deliverable version for
  collaborators (with column definitions, method, limitations and provenance).
- **Validation**: W91Re9 (DFT_0001) agrees with single-crystal experiment on pure W to within
  a few % for every elastic constant (C11 533 vs 522, C44 158 vs 161, B 306 vs 310 GPa).

Key findings (see `docs/stage3-report.md` for details):

- **Convergence tuning**: elastic distortions break cubic symmetry and are harder to converge
  than EOS. The full library reached 100% via an **outlier guard** plus **tiered
  depth/AMIX/IEX** settings (`_params_for` in `config.py`) — Hf-containing alloys use mixed
  depth (B0@0.95 + C′@shallow), the Ta-rich corner needs deeper depth, and DFT_0198 was fixed
  with IEX=3 (VWN) to cure the divergence of the Hf 4f atomic solution.
- **AMIX physics** (§5.1): slow AMIX pins the ground state for bistable Hf alloys (the cure),
  but breaks the Fermi search for V-rich alloys with a sharp DOS (the poison); the true test of
  data health is **fit quality, not the raw energy gap**.
- **Born instability pattern** (§4.1): **all** 12 alloys with C′≤0 fall in the low-VEC (≤4.5)
  + Hf-enriched corner, consistent with the physics of group-4 (Ti/Zr/Hf) BCC being
  mechanically metastable at 0 K — no counterexample across all 1598 alloys.

> **Raw DFT data is not under version control**: the per-point intermediates under
> `stageN_*/DFT_XXXX/` (~98 GB) can be regenerated from `run_pipeline.py --generate` +
> `structures/`, and every load-bearing quantity has been extracted into `results/*.csv`. See
> `docs/archive-manifest.md` for local cleanup and regeneration.

## Calculation parameters

| Item | Value |
| --- | --- |
| Structure | BCC (CPA for the disordered alloys) |
| Exchange-correlation functional | PBE |
| Magnetism | Non-magnetic (`afm='P'`) |
| Expansion | Single expansion (`expan='S'`) |
| Core states | Soft core (`sofc='Y'`) |
| All other KGRN/KFCD parameters | pyemto defaults |

## Three-stage workflow

```
CSV (1598 compositions)
   │  vegard.py:  SWS_guess = Σ (c_i/100) · SWS_i
   ▼
Stage 1  coarse EOS   6 points, SWS_guess ±3%   → stage1_eos_coarse/DFT_XXXX/
   │  (user submits to cluster) → analyse → SWS0, B0
   │      ├─ minimum at or beyond the edge of the sampled range → written to the
   │      │  retry queue (shifted centre) → regenerate with --retry
   │      └─ EMTO error → stage1_errors.csv
   ▼
Stage 2  fine EOS     11 points, SWS0 ±1.5%     → stage2_eos_fine/DFT_XXXX/
   │  (submit to cluster) → analyse → accurate SWS0, B0
   ▼
Stage 3  elastic constants (from the stage2 SWS0/B0) → stage3_elastic/DFT_XXXX/
   │  (submit to cluster) → analyse → C11, C12, C44 + mechanical properties
   ▼
results/final_mechanical_properties.csv
```

Every stage is the same manual three-step loop: **generate → user submits to the cluster →
analyse**. Both generation and analysis skip directories that already exist and DFT_IDs whose
results have already been written, so they are safe to re-run.

## Usage

```bash
# Stage 1: generate the coarse-scan input (structure directory given by --latpath)
python run_pipeline.py --stage 1 --generate --latpath /path/to/structures

# ——— the user submits the jobs under stage1_eos_coarse/ to the cluster and waits ———

# Stage 1: fit the EOS, write out SWS0/B0, and build the retry queue
python run_pipeline.py --stage 1 --analyze

# For alloys whose fitted minimum landed at the edge, regenerate the input around a shifted SWS centre
python run_pipeline.py --stage 1 --retry
# (re-submit, then --analyze again)

# Stage 2: fine scan
python run_pipeline.py --stage 2 --generate
python run_pipeline.py --stage 2 --analyze

# Stage 3: elastic constants and mechanical properties
python run_pipeline.py --stage 3 --generate
python run_pipeline.py --stage 3 --analyze

# Error summary (without --stage it summarises all three stages)
python run_pipeline.py --errors
python run_pipeline.py --errors --stage 1
```

### Command-line options

| Option | Description |
| --- | --- |
| `--stage {1,2,3}` | Stage number; required except with `--errors` |
| `--generate` | Generate the EMTO input files for that stage |
| `--analyze` | Analyse the completed output of that stage |
| `--retry` | Regenerate input from the retry queue (stage 1 only) |
| `--errors` | Print the error summary |
| `--latpath PATH` | Directory holding KSTR/BMDL/SHAPE, default `/work/scratch/md88vyxi/workplace/highthroughput-dft-rhea/structures` |

## Cluster submission (Slurm)

Once a stage's input has been generated, submit it to Lichtenberg with `jobs/submit_stage.sh`:

```bash
# Smoke test: fill one node with the first 96 tasks to get a runtime distribution
jobs/submit_stage.sh 1 --limit 96 --chunk 96 --time 02:00:00

# Full submission once the parameters are calibrated
jobs/submit_stage.sh 1
```

| Option | Default | Description |
| --- | --- | --- |
| `--chunk N` | 1000 | Tasks per chunk; one chunk is consumed by one 96-core node |
| `--maxpar N` | 8 | Maximum array tasks (nodes) running at once |
| `--time HH:MM:SS` | 24:00:00 | Time limit for a single array task |
| `--partition P` / `-p P` | `deflt` | Partition |
| `--account A` | `p0020537` | Slurm account |
| `--limit N` | 0 (all) | Take only the first N unfinished tasks; 0 means no limit |
| `--dry-run` | | Only print the statistics and the sbatch command — write nothing, submit nothing |

`stage` must be `1`, `2` or `3`; `--chunk`/`--maxpar` must be positive integers and `--limit`
a non-negative integer. If an option value is invalid or missing, the script prints an error and
exits with code 2 without submitting any job.

The script scans `stageN_*/DFT_XXXX/*.kgrn`, **skips any point whose `kfcd/<job>.prn` already
contains `FINISHED`**, writes the remaining points as chunks into
`jobs/worklists/stageN_<timestamp>/`, and submits one Slurm array job. So **re-running is
simply issuing the same command again** — resuming after an interruption, filling in timed-out
points, and topping up after a `--retry` regeneration all need no manual selection of alloys.

Note that re-running only converges if the failure was an **interruption** (timeout, node
failure, etc.): a point that genuinely keeps crashing or never converges will be queued into the
worklist again unchanged on every run, burning up to `EMTO_TIMEOUT` seconds each time before
failing, and will never stop retrying by itself. Such points have to be identified with
`python run_pipeline.py --stage N --analyze` / `--errors` and handled manually, or given adjusted
parameters and then re-run through `--retry`.

What each of the three scripts does:

| Script | Responsibility |
| --- | --- |
| `jobs/submit_stage.sh` | Scan for unfinished points → chunk them → `sbatch` |
| `jobs/job_array.sh` | The array job body: load the module, consume one chunk with `xargs -P 96` |
| `jobs/run_one.sh` | Run one point: `cd` into the alloy directory, skip idempotently, guard with `timeout`, record runtime; also clears intermediates when `EMTO_CLEANUP=1` |

Every point that finishes (successfully or not) appends one line to
`jobs/worklists/<this run>/timing.log`, formatted `<jobname> <kgrn seconds> <kfcd seconds>
<exit code>`. Points that were skipped idempotently (already `FINISHED` from an earlier run) are
not recorded, so the line count does not equal the total number of tasks in that worklist — it
only reflects the points actually run this time. Use it to calibrate `--chunk` and
`EMTO_TIMEOUT`:

- `--chunk` ≈ 96 × target chunk duration (3–4 h) / mean runtime per point
- `EMTO_TIMEOUT` ≈ 3–4 × the runtime of the slowest point (default 7200 seconds)

### Environment variables (`jobs/run_one.sh` / `jobs/job_array.sh`)

`run_one.sh` / `job_array.sh` themselves run on the compute nodes and take no command-line
arguments. All of the variables below have to be set on **the `submit_stage.sh` command line that
submits the job**, from where `sbatch --export=ALL` carries them unchanged to the compute nodes —
not by logging into a compute node and setting them there:

```bash
EMTO_TIMEOUT=10800 EMTO_NPROC=48 EMTO_CLEANUP=1 jobs/submit_stage.sh 1
```

| Variable | Default | Description |
| --- | --- | --- |
| `EMTO_TIMEOUT` | 7200 | Wall-clock limit for a single KGRN/KFCD binary (seconds) |
| `EMTO_CLEANUP` | unset (no cleanup) | Only when set to `1` are the large intermediates — `.atm/.chd/.pot/.zms`, `kgrn/tmp/` and so on — deleted; `.prn` is always kept for the analysis stage to parse |
| `WORKLIST_DIR` | (passed in by `submit_stage.sh`) | When non-empty, timings are appended to `$WORKLIST_DIR/timing.log`; overriding it by hand is not recommended |
| `EMTO_NPROC` | 96 | Concurrency for `xargs -P` inside `job_array.sh` |
| `EMTO_BIN` | `$HOME/intel-mkl-omp-build-2021-Mar/bin` | Directory holding the EMTO binaries |

`EMTO_CLEANUP` is off by default: during smoke testing the `.pot`/`.chd` files are needed to
debug SCF convergence. But in a full production run, keeping these potential and charge-density
files for all 46000 points would quickly exhaust the scratch quota, so large submissions should
set `EMTO_CLEANUP=1` explicitly:

```bash
EMTO_CLEANUP=1 jobs/submit_stage.sh 1
```

The complete flow:

```bash
python run_pipeline.py --stage 1 --generate
jobs/submit_stage.sh 1 --limit 96 --chunk 96 --time 02:00:00   # smoke test
EMTO_CLEANUP=1 jobs/submit_stage.sh 1                           # full run
python run_pipeline.py --stage 1 --analyze
python run_pipeline.py --stage 1 --retry
EMTO_CLEANUP=1 jobs/submit_stage.sh 1                           # top-up
python run_pipeline.py --stage 1 --analyze
```

Stages 2 and 3 work the same way.

### Tests

The submission scripts come with a pure-bash test suite (no Slurm, EMTO binaries, pytest or
bats required):

```bash
bash jobs/tests/run_all.sh
```

## Output files

Everything is written to `results/` as CSVs that can be appended to incrementally:

| File | Contents |
| --- | --- |
| `stage1_coarse_results.csv` | `DFT_ID, Alloy, SWS0, B0` (coarse scan) |
| `stage1_retry_queue.csv` | `DFT_ID, Alloy, old_sws_center, new_sws_center, reason, retry_round` |
| `stage2_fine_results.csv` | `DFT_ID, Alloy, SWS0, B0` (fine scan, used by stage3) |
| `stage3_elastic_r2.csv` | R² and number of outliers dropped for each alloy's C′/C44 distortion fit |
| `final_mechanical_properties.csv` | All 1598 rows: SWS0, B0, C11/C12/C44/C′ and derived mechanical quantities + R² + Born stability |
| `stageN_errors.csv` | `DFT_ID, Alloy, SWS, error_type, message` |

**The deliverable version for collaborators** (tracked in `git`, with documentation):

| File | Contents |
| --- | --- |
| `20260723-…-groundstate-confirmed-1598-….csv` | Full-library deliverable (same content as `final_mechanical_properties.csv`) |
| `README-elastic-mechanical-properties.md` | Definitions of the 23 columns, method, interpretation, known limitations, provenance |
| `20260722-…基态确认1480条….csv` | Historical v1 (kept so the README can document the evolution) |

The columns of `final_mechanical_properties.csv`: `SWS0, B0, C11, C12, C44, cprime, B,
G_V, G_R, G_VRH, E, nu, B_G_ratio, Cauchy, A, Hv, R2_cprime, R2_c44,
n_drop_cprime, n_drop_c44, born_stable`. The derived quantities: bulk modulus `B`; shear moduli
`G_V`/`G_R`/`G_VRH` (Voigt–Reuss–Hill); Young's modulus `E`; Poisson's ratio `nu`;
`B_G_ratio` (Pugh's ratio); Cauchy pressure `Cauchy = C12 − C44`; anisotropy factor
`A = 2C44/(C11 − C12)`; empirical hardness `Hv = 2(k²G)^0.585 − 3` (with `k = G/B`);
`R2_*`/`n_drop_*` are the quality of the distortion fit and the number of points removed by the
outlier guard; `born_stable` is Born mechanical stability (Y/N).

## Module structure

| File | Responsibility |
| --- | --- |
| `config.py` | Constants: elemental Wigner–Seitz radii, EMTO parameters, directory names, number and range of sampling points |
| `vegard.py` | Vegard's-law estimate of the initial SWS; checks that the concentrations sum to 100 |
| `emto_generator.py` | CSV parsing; calls pyemto to generate the EOS / elastic-constant input |
| `eos_analysis.py` | EOS fitting, coarse-fit quality check (`check_coarse_fit`), and writing the retry queue |
| `elastic_analysis.py` | Parses the elastic-constant output and computes the mechanical properties |
| `error_collector.py` | Scans the kgrn/kfcd output, classifies errors and summarises them |
| `run_pipeline.py` | CLI entry point, chaining the stages together |
| `jobs/submit_stage.sh` | Scans for unfinished tasks, chunks them, submits the Slurm array job |
| `jobs/job_array.sh` | The array job body; each node consumes one worklist chunk with `xargs -P 96` |
| `jobs/run_one.sh` | Single-point executor: idempotent, timeout-guarded, timed; clears intermediates when `EMTO_CLEANUP=1` |

### Error types

`error_collector.py` checks `kgrn/*.prn` and `kfcd/*.prn` job by job, and can report:

- `missing_output` — the kfcd output is missing or empty
- `scf_not_converged` — `NOT CONVERGED` appears in the KGRN output
- `no_energy` — neither `TOT-PBE` nor `TOT-LDA` is found in the kfcd output
- `nan_energy` — the total energy is NaN or cannot be parsed

Additional guards on the EOS fit: fewer than 4 valid SWS points, an exception raised during the
fit, `B0 ≤ 0`, or `B0 > 1000 GPa` all count as failures and go into the retry queue (stage 1).

## Dependencies

- Python 3
- `numpy`
- `pyemto`
- `pytest` (tests only)

## Tests

The tests import the top-level modules directly, so they must be run from the repository root:

```bash
python -m pytest tests/
```

## Documentation

- **stage3 elastic-constant report**: `docs/stage3-report.md` — method, full-library results,
  §4.1 the compositional pattern of Born instability, §5 the tiers of convergence tuning,
  §5.1 AMIX physics
- **stage2 fine-scan EOS report**: `docs/stage2-summary-report.md`
- **Deliverable documentation**: `results/README-elastic-mechanical-properties.md`
- **Archive / cleanup manifest**: `docs/archive-manifest.md` — per-directory deletion commands
  for the raw DFT output, plus how to regenerate it
- Design documents: `docs/superpowers/specs/2026-07-20-highthroughput-emto-rhea-design.md`,
  `docs/superpowers/specs/2026-07-23-repo-github-vs-archive-design.md`
- Implementation plan: `docs/superpowers/plans/2026-07-20-highthroughput-emto-rhea.md`

## License

[MIT](LICENSE)
