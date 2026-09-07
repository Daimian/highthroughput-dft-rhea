# Stage 2 (fine EOS) results summary

English | [中文](stage2-summary-report.zh.md)

Date: 2026-07-21　|　Method: EMTO-CPA / PBE, BCC, Morse EOS fit (11 points over a fine ±1.5% window)

## 1. Overall completion

**All 1598 / 1598 alloys fitted successfully (100%)**, and the retry queue is empty.

## 2. Physical results

| Quantity | Result |
|---|---|
| **B0, bulk modulus** | 77 – 306 GPa, median **160**, mean 160 |
| B0 percentiles (5/25/50/75/95) | 118 / 142 / 160 / 176 / 207 GPa |
| **Equilibrium sws0** | 2.905 – 3.325 Bohr |

**The extremes match chemical intuition**: the softest alloys are Ti/Zr-rich (B0 ~77–95) and the
hardest are W/Re-rich (W91Re9 = 306). The B0 distribution is bell-shaped and peaks at 150–175 GPa,
which is entirely reasonable for refractory BCC HEAs.

## 3. Fit quality

| Metric | Result |
|---|---|
| **Healthy** (\|dSWS\|<0.015 and R²≥0.99) | **1563 / 1598 (97.8%)** |
| R² ≥ 0.999 | 1522 |
| R² 0.95–0.99 | 2 |
| R² < 0.95 | 7 (inherent to a shallow well + a fine window; B0 is still physical) |
| sws0 well centred, \|dSWS\|<0.015 | 1572 |
| \|dSWS\| ≥ 0.03 (slightly off-centre) | 9 (sws0 is bracketed by the data in every case, so the interpolation is reliable) |

## 4. Convergence method (established in this round)

The Ta-rich / multi-state corner reached 100% through the following mechanisms:

- **Per-point, volume-aware EFGS** (Σconc·coefficient + sws) plus an extrapolation margin
- **Outlier energy guard**: after clustering, keep the **lowest-energy cluster that has ≥3 points**
  (= the ground state), which screens out metastable states and spurious points
- **Convergence coverage**: `Ta≥30 → depth 0.80 + AMIX 0.02`, plus an explicit list (9 alloys with
  low Ta that nevertheless fell into a metastable state or scattered)
- **A B0 upper bound of 350 GPa** to block unphysical fits

The key physical insight: **electronic bistability is widespread in refractory HEAs**, and the EOS
must be fitted to the **ground-state cluster**. **It is AMIX (charge mixing), not EFMIX, that decides
which electronic state the SCF falls into** — AMIX=0.02 collapses the multiple states onto a single
ground state.

## 5. Known limitations (please note when using the data)

1. **R² means little over a fine window**: over a ±1.5% window the energy only changes by 1–2 mRy
   (∝B0), so soft alloys naturally have a lower R² — **judge by whether B0 is physical and whether
   sws0 is bracketed, not by R² alone**.
2. **B′ and the Grüneisen parameter are not usable**: Morse pins B′ at 4, and over a narrow window
   BM cannot constrain B′ (for the same EOS, the B′=4 and B′=−0.26 curves coincide). A genuine B′
   would require a BM fit over the coarse window (stage1, ±3%).
3. **Absolute B0 values**: W/Mo-rich alloys come out accurate (W91Re9 = 306 vs 310 in experiment);
   **Nb-rich alloys have a median of 164 GPa vs ~170 in experiment, which is broadly reasonable**
   (individual cases such as Nb96 come out as soft as 146, a mild underestimate from the EMTO
   spherical approximation plus PBE for Nb).
4. **9 slightly off-centre alloys** (\|dSWS\| 0.03–0.11, mostly soft alloys): both sws0 and B0 are
   usable; this comes from the slow geometric convergence of a shallow well, not from a bad fit.

## 6. Data file

`results/stage2_fine_results.csv`: `DFT_ID, Alloy, SWS0, B0, R2, dSWS_center`

## 7. Conclusion

The stage2 fine EOS **converged for all 1598/1598 alloys and is physically self-consistent**, giving
a reliable **equilibrium volume sws0** and **bulk modulus B0**. These can serve as the input volume
for stage3 (elastic constants). Structural stability has to be judged from the stage3 elastic
constants (the Born criteria on C′ and C44) — the EOS only reflects the hydrostatic response.
