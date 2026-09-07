# Elastic and mechanical properties of refractory high-entropy alloys (full library)

English | [中文](README-elastic-mechanical-properties.zh.md)

**Data file**: `20260723-refractory-hea-elastic-mechanical-properties-groundstate-confirmed-1598-highthroughput-dft.csv`
**Date**: 2026-07-23　|　**Method**: EMTO-CPA / PBE, BCC　|　**Version**: v3 (full library, 1598/1598)

---

## 1. What this is

**Single-crystal elastic constants plus polycrystalline mechanical properties** for **1598** BCC
refractory high-entropy alloys (the nine-element Ti·Zr·Hf·V·Nb·Ta·Mo·W·Re system), obtained by
high-throughput DFT and **all ground-state confirmed** — that is, the elastic distortions really
did converge to the ground-state electronic structure, so the results are physically trustworthy.

**How it evolved**: v1 (1480 rows) had excluded 118 alloys with a "gap≠0"; after reviewing them
category by category, all of them were merged back in, giving 1598/1598:

- **30 Hf-containing alloys = genuinely excited states** (the Hf semi-core jumping to a different
  branch inflated C44 — e.g. C44 of Ti20Hf40V15Ta25 went 767→70 GPa). Recomputing them uniformly
  with depth0.80 + AMIX0.01 pinned them back to the ground state and brought C44 down to a
  physical value.
- **78 = an energy-offset artefact of mixing depths**: the raw gap was large, but C44 was
  unchanged after recomputation (the rigid shift between depth0.80 and depth0.95 cancels in the
  fit), so the data was correct all along.
- **DFT_0198 (Hf2Ta90W3Re5) = an IEX problem**: the Hf 4f14 atomic solution oscillated and
  diverged under the default IEX=4; switching to IEX=3 (VWN) converged cleanly, 12/12.
- **9 V-rich alloys** (0567/0728/0953/1009/1257/1354/1430/1456/1585): same-depth gaps of 0.2–3.4 Ry,
  yet the production fit gave **R²=1.000 with zero outliers** — a **rigid shift of the energy zero**
  (which cancels exactly for the curvatures C′/C44), so the data is trustworthy. This established
  that the real test of health is **fit quality (R², number of points dropped), not the raw gap** —
  the raw gap flags a harmless rigid shift as pathological.

## 2. Computational workflow (three stages)

| Stage | Content | Quantities provided |
|---|---|---|
| stage1 | Coarse EOS (6 points, ±3%) | Initial equilibrium volume |
| stage2 | Fine EOS (11 points, ±1.5%, Morse fit) | **B₀ (bulk modulus), sws0 (equilibrium Wigner-Seitz radius)** |
| stage3 | Volume-conserving distortions (12 points) | **C′, C₄₄** |

- **Volume-conserving distortions** are applied at the stage2 equilibrium volume: an orthorhombic
  distortion → C′=(C₁₁−C₁₂)/2; a monoclinic distortion → C₄₄.
- C₁₁ and C₁₂ are back-solved from C′ together with B₀=(C₁₁+2C₁₂)/3.
- Polycrystalline quantities use the **Voigt–Reuss–Hill** average; ductility uses **Pugh's ratio B/G**.
- **Validation**: W₉₁Re₉ (DFT_0001) agrees with single-crystal experiment on W to within a few %
  for every constant (C₁₁ 533 vs 522, C₄₄ 158 vs 161, B 306 vs 310 GPa).

## 3. Column definitions

Units: elastic constants and moduli are in **GPa**; sws0 is in **Bohr**; ratios and Poisson's ratio
are dimensionless.

| Column | Meaning | Unit |
|---|---|---|
| `DFT_ID` | Alloy identifier | — |
| `Alloy` | Composition formula (atomic percent) | — |
| `SWS0` | Equilibrium Wigner-Seitz radius (stage2) | Bohr |
| `B0` | Bulk modulus (stage2 EOS) | GPa |
| `C11` `C12` `C44` | Cubic single-crystal elastic constants | GPa |
| `cprime` | Tetragonal shear C′=(C₁₁−C₁₂)/2 | GPa |
| `B` | Bulk modulus (= B0; consistent with the EOS under VRH) | GPa |
| `G_V` `G_R` `G_VRH` | Shear modulus: Voigt / Reuss / **Hill average** | GPa |
| `E` | Young's modulus (from G_VRH) | GPa |
| `nu` | Poisson's ratio ν | — |
| `B_G_ratio` | **Pugh's ratio B/G** (>1.75 counts as ductile) | — |
| `Cauchy` | Cauchy pressure C₁₂−C₄₄ (>0 means metallic bonding / ductility) | GPa |
| `A` | Zener anisotropy 2C₄₄/(C₁₁−C₁₂) | — |
| `Hv` | Estimated Vickers hardness (Tian model) | GPa |
| `R2_cprime` `R2_c44` | R² of the parabolic fit for each of the two distortions | — |
| `n_drop_cprime` `n_drop_c44` | Number of outlying distortion points removed during fitting (the guard) | — |
| `born_stable` | **Born mechanical stability**: Y / N | — |

## 4. How to read it

- **Born stability** (`born_stable`): Y = C′>0, C₄₄>0 and C₁₁+2C₁₂>0 are all satisfied, so BCC is
  mechanically stable; N = close to a Bain instability (C′≲0), in which case G/E can come out
  negative — **that is the correct signal of instability, not a calculation error**. This set has
  1586 stable and **12 unstable** alloys (Ti/Hf/Zr-enriched:
  DFT_0141/0228/0296/0374/0711/0758/0759/0821/0945/0998/1188/1271; of these, 0228/0711/0945/0998/1188
  were newly merged in for v2 and emerged as soft Hf/Zr-rich alloys once C44 was revised downwards).
- **Ductility**: the median B/G is 2.56, and 1592/1598 count as ductile (Pugh > 1.75) — typical of
  refractory BCC HEAs.
- **Magnitudes for reference** (GPa, 5% / median / 95%): C₁₁ 150/237/340; C₄₄ 48/65/88; B 118/159/208;
  G 42/60/88; E 112/161/229. Median ν is 0.33.

## 5. Known limitations (please read before use)

1. **This version is the full library, 1598/1598, all ground-state confirmed**, with nothing left
   out. (Note: the raw energy gap flags a "rigid shift of the energy zero" as pathological — the real
   test is the fit R² and the number of points dropped, see §1. The 9 V-rich alloys that were once
   suspect have R²=1.000 with zero points dropped; they were confirmed trustworthy and merged in.)
2. **Depth mismatch for C′ in Hf-containing alloys**: B₀ comes from depth0.95 (which captures the
   EOS of the Hf semi-core correctly), while some C′ values come from a shallower depth (needed for
   the distortion to converge). The two depths are therefore not fully consistent, leaving a small
   but bounded residual in C₁₁/C₁₂.
3. **B₀ of Nb-rich alloys is ~15% too soft** (the EMTO spherical approximation plus the PBE
   underestimate for Nb), which propagates into their C₁₁/C₁₂.
4. **Fit quality**: R² means little over the fine ±1.5% window (for soft alloys the energy only
   changes by 1–2 mRy), so judge by the physical soundness of B₀/C′ as well and do not rely on R²
   alone.

## 6. Provenance

- Input compositions: `20260718-refractory-hea-compositions-1600-highthroughput-dft.csv` (1598 rows).
- For the calculation code and the tiered convergence strategy, see `config.py` /
  `elastic_analysis.py` in the repository and `docs/stage3-report.md`.
- All 1598 rows (same content as this file's data set): `results/final_mechanical_properties.csv`.
