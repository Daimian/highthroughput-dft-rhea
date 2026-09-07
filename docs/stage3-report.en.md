# Stage 3 (elastic constants) report

English | [中文](stage3-report.md)

Date: 2026-07-21　|　Method: EMTO-CPA / PBE, BCC, volume-conserving distortions

## 1. Method

Volume-conserving distortions are applied at each alloy's stage2 equilibrium volume sws0, and the
elastic constants are extracted from the energy-strain curve:

- **Orthorhombic distortion** (`bcco0–5`, 6 strains) → tetragonal shear **C′ = (C11 − C12)/2**
- **Monoclinic distortion** (`bccm0–5`, 6 strains) → **C44**
- **C11 and C12** are back-solved from C′ together with the stage2 bulk modulus
  **B0 = (C11 + 2·C12)/3**

So stage3 uses two quantities from stage2: **sws0 (which fixes the volume)** and **B0 (which fixes
C11/C12)**.

The polycrystalline aggregate quantities use the **Voigt-Reuss-Hill** average[^hill], and ductility
uses **Pugh's ratio B/G**[^pugh].

## 2. First test: DFT_0001 (W91Re9)

All 12 distortion points converged. Input sws0 = 2.9638 Bohr, B0 = 305.6 GPa.

| Quantity (GPa unless noted) | This work | W experiment[^fn1963] | Deviation |
|---|---|---|---|
| C11 | **533.2** | 522.4 | +2% |
| C12 | **191.8** | 204.4 | −6% |
| C44 | **157.6** | 160.8 | −2% |
| B (bulk modulus) | 305.6 | 310.4 | −2% |
| C′ | 170.7 | 159.0 | +7% |
| G (shear, Hill) | 162.7 | 160 | +2% |
| E (Young's) | 414.5 | 410 | +1% |
| ν (Poisson's ratio) | 0.274 | 0.280 | — |
| B/G (Pugh) | 1.88 | 1.94 | — |
| A (Zener anisotropy) | 0.92 | 0.92 | — |

**Excellent agreement with single-crystal experiment on pure W** (every quantity within a few %).
W91Re9 is mostly W and should be close to pure W — this agreement validates the whole stage3 chain
(distortion generation → convergence → `fit_elastic(sws0,B0)` → elastic constants).

## 3. Born mechanical stability (BCC)

Criteria: C′ > 0, C44 > 0, C11 + 2C12 > 0.

DFT_0001: **C′ = 171 > 0, C44 = 158 > 0, C11+2C12 = 917 > 0 → BCC is mechanically stable** ✅

(Structural stability is judged from the elastic constants; the EOS only reflects the hydrostatic
response. C′→0 or negative = BCC is unstable along the Bain path.)

## 4. Full-library results (1598 / 1598 = 100%)

`results/final_mechanical_properties.csv`: C11/C12/C44/cprime + B/G_V/G_R/G_VRH/E/nu/B_G_ratio/
Cauchy/A/Hv + R2_cprime/R2_c44/n_drop_*/born_stable.

| Quantity (GPa) | 5% | Median | 95% |
|---|---|---|---|
| C11 | 149 | 237 | 339 |
| C12 | 96 | 119 | 144 |
| C44 | 48 | 65 | 89 |
| B | 118 | 160 | 207 |
| G(VRH) | 41 | 61 | 88 |
| E | 109 | 161 | 229 |

The median ν is 0.33 and the median B/G is 2.56. **Born mechanically stable: 1586/1598 (99.2%)**,
with 12 Ti/Hf/Zr-rich alloys close to a Bain instability (C′≲0, including the 5 soft alloys
0228/0711/0945/0998/1188 that only emerged once the g118 review revised C44 downwards); **Pugh
ductile (B/G>1.75): 1592/1598 (≈100%)** — typical of refractory BCC HEAs. (The statistics are based
on the final full library after the g118 review, see §5.1.)

## 4.1 The compositional pattern of Born instability (tested over the full library)

All 12 Born-unstable alloys **have C′≤0** (tetragonal-shear / Bain instability; C44 and C11+2C12 are
both normal). A composition-elasticity regression test over all 1598 alloys gives a conclusion in
three layers — one main rule validated across the full library, one **correction** to an earlier
generalisation, and one refinement:

**① The main axis C′–VEC: monotonic, no counterexamples (strong).** The median C′ rises
monotonically with valence electron concentration VEC (16 GPa in the 4.0–4.2 band → 136 GPa in the
5.5–6.1 band), and **every instability falls at VEC≤4.5** — the 1284 alloys with VEC>4.5 have **zero**
instabilities, with no counterexample in the whole library. The 10 lowest-C′ alloys in the library
also all sit in the low-VEC corner at VEC≤4.48. This directly confirms that C′ is set by the
bonding-antibonding filling of the d band: low filling → soft tetragonal shear → BCC unstable along
the Bain path. (VEC: Ti/Zr/Hf=4, V/Nb/Ta=5, Cr/Mo/W=6, Re=7.)

**② Correction: "group-4 enrichment" is not an independent criterion.** VEC≤4.5 is **necessary but
not sufficient** — only 12 of the 250 alloys in that pool (5%) are unstable. Comparing unstable
against stable within the pool, the **group-4 (Ti+Zr+Hf) fraction is 69% vs 67% — essentially
indistinguishable**. The low-VEC region contains plenty of very stable group-4-rich alloys with even
lower VEC and even more group 4 than the unstable ones (e.g. Ti48Zr42Nb5Ta5: VEC 4.10, 90% group 4,
**C′=+11.9, stable**; versus the Hf40Ta45 family at VEC 4.45 with C′<0). So "lots of group 4" cannot
be used to predict instability.

**③ Refinement: the real second axis is the Hf content.** Looking element by element at the
separation within the low-VEC pool, only **Hf stands out (mean 39% in the unstable group vs 19% in
the stable one — the only 2× difference)**; Ti is in fact lower among the unstable ones (15% vs 25%),
and Nb is a clear stabiliser (2% vs 12%, raising VEC and stabilising BCC at the same time). **The
corrected rule: it takes low VEC (≤4.5) *and* Hf enrichment (typically Hf≥40) to actually cross the
instability boundary.** Physically, all three group-4 elements have an HCP ground state and are BCC-
metastable at 0 K, but Hf-rich BCC has the softest tetragonal shear (the strong ω/β instability
tendency of Hf/Zr plus the Hf 5d²/4f semi-core) — this is a data-driven observation; the microscopic
mechanism awaits confirmation against pure-element/binary C′ references.

**Credibility of the data**: all 12 unstable alloys have C′≤0 with normal C44, a high fit R² and no
anomalous point rejections → **a physically real signal of single-phase BCC instability, not bad
data**. Five of them (0228/0711/0945/0998/1188) only appeared once the g118 ground-state correction
of §5.1 pulled their inflated C44 back down — what surfaced after fixing the electronic structure is
a physically self-consistent low-VEC/Hf instability, which argues that the correction was right.
These alloys are unstable as single-phase BCC at 0 K and may in practice be multiphase, martensitic,
or metastable at high temperature; they should be flagged or excluded when the data is used as
single-phase BCC elasticity.

## 5. Convergence tuning (established in this round; the tiers in `_params_for` in config)

Elastic distortions **break cubic symmetry and are harder to converge than the EOS**, and each alloy
has a narrow "distortion convergence window". The full library reached 100% via the outlier guard
plus tiered depth/AMIX/IEX:

- **Outlier guard** (`elastic_analysis`): among the 6 points of a distortion, points that fell into
  a spurious electronic state are dropped (by absolute gap and by statistics); ≥4 points are enough
  to fit, and a negative C′ is accepted. This one change alone took 84% → 92%.
- **depth is the main convergence lever, and it is not energy-neutral** (it changes C′): the Ta+V-rich
  corner needs depth0.70, Ta-containing alloys generally need 0.80, and the pure refractory metals
  are fine at 0.95.
- **⚠️ depth conflicts with the EOS of Hf-containing alloys**: depth≤0.90 corrupts the EOS of Hf-rich
  alloys (a spurious expanded, soft state). Hf-containing alloys therefore use a **mixed depth**:
  B0/sws0 from depth0.95 (the correct EOS), and the distortions from the shallowest depth that
  converges (C′@shallow + B0@0.95, with a footnote).
- **AMIX selects the electronic basin (energy-neutral)**: a slow AMIX pins a single basin. The
  **high-Hf scattering corner** uses **AMIX=0.01** (slower than 0.02) to pin all 12 points into the
  ground state. But a slow AMIX is **not a cure-all** — for V-rich alloys it is in fact fatal (§5.1).
- **IEX (the XC of the atomic solver)**: for DFT_0198 (Hf2Ta90), the Hf 4f14 Dirac atomic solution
  oscillated and diverged under the default **IEX=4 (PW92)** (ATOMC "Too few iterations";
  depth/dirac_niter/sofc/lmaxh all made no difference, while pure Ta100 converged with the same
  parameters → the problem lies in the atomic XC potential of the trace Hf). Switching to
  **IEX=3 (VWN)** converged cleanly (digit for digit identical to 6=PZ, i.e. the LDA answer PW92
  should have given), consistent with the library-wide LDA-SCF methodology and requiring no change
  to the composition.

The tiers (`_params_for`, highest priority first): `D70_ALLOYS` (18, depth0.70) ·
`HF_SCATTER_A01_ALLOYS` (4, depth0.80+AMIX0.01) · Ta≥30/`DEEP_TA_ALLOYS` (depth0.80) ·
`HF_D80_ALLOYS` (33, depth0.80 mixed) · `MIXED_HF_ALLOYS` (60, depth0.90 mixed) ·
`AMIX_ONLY_ALLOYS` (16, depth0.95) · `IEX_OVERRIDE={DFT_0198:3}`.

**KGRN IEX value table** (extracted with `strings` from the binary, 0-indexed): 0 Barth-Hedin ·
1 X-Alpha · 2 Barth-Hedin-Janak · 3 VWN · **4 Perdew-Wang PW92 (default, LDA)** · 5 Wigner ·
6 Perdew-Zunger · **7 PBE (GGA)** · 8 Local-Airy-Gas · 9 PBEsol. pyemto does not couple xc to iex:
the KGRN SCF is done under IEX (LDA), and KFCD then applies the xc=PBE correction.

## 5.1 The two roles of AMIX and the convergence paradox of V-rich alloys

AMIX is the **linear charge/potential mixing coefficient** between SCF iterations:
$n_{\text{in}}^{(k+1)}=(1-\text{AMIX})\,n_{\text{in}}^{(k)}+\text{AMIX}\,n_{\text{out}}^{(k)}$ — each
step adopts only a small part of the new density. It plays **two independent roles**, and which one
dominates depends on the alloy's electronic structure. That explains a paradox: **the same act of
"slowing AMIX down" is the cure for Hf and the poison for V-rich alloys.**

- **Role one · basin selection (good for Hf)**: the Hf40 scattering alloys are **bistable** (the
  ground state and the Hf semi-core excited state are close in energy); the SCF *does* converge, it
  just falls into the wrong well. A slow AMIX = moving only a little each step = **never leaving the
  basin of the initial guess (overlapping atomic potentials ≈ the ground state)**, which pins all 12
  distortion points into the ground state. Here AMIX is purely a "basin selector"; fast or slow, it
  converges.
- **Role two · whether self-consistency is reachable within the iteration budget (fatal for V-rich
  alloys)**: in V-rich alloys (V 26–40, usually with Ti/Zr) **E_F sits right on a tall, steep d-state
  density of states** (group-5 V in BCC has few d electrons, putting E_F on the steep flank of the d
  peak; adding Ti/Zr pushes E_F further up the peak). A small change in the potential sweeps the sharp
  peak across E_F → the occupation oscillates violently = **charge sloshing**; and the distortion
  additionally **splits** the peak (a band Jahn–Teller-like effect), making E_F harder to locate in
  the distorted cell than in the cubic one. For such a stiff system, AMIX has a **Goldilocks window**:
  too fast → overshoot and divergence; **too slow (0.01) → each step barely corrects anything and
  self-consistency is simply never reached within the NITER iteration limit**, leaving a half-converged,
  internally inconsistent density whose DOS near E_F is still jagged, so the moment-method Fermi search
  `EFXMOM` cannot find a self-consistent E_F → it reports **"Fermi level not found"**. The
  **default AMIX** used in production sits inside this window → 12/12 converge.

**Why "slower" is not universal**: the convergence rate of linear mixing goes as $\sim(1-\alpha J)$,
and a sharp DOS makes the effective eigenvalues of the SCF-map Jacobian $J$ very large. Reducing
$\alpha$ **does not improve the condition number** — it just slows everything down so that convergence
is not reached before the iterations run out. The lever that actually addresses this is **smoothing the
sharp peak with Fermi broadening / electronic temperature (raise `EFMIX` or use smearing)**, or
**Kerker/Broyden mixing** — not a smaller linear α.

**Empirical evidence (2026-07-23, job 53541052 / `stage3_v9`)**: at depth0.95+AMIX0.01, the 9 V-rich
alloys converged only 6 of 108 points (the rest all gave `EFXMOM: Fermi level not found`). But they
**never needed recomputing at all** — the production fit (with the default AMIX) gives **R²=1.000,
zero points dropped, Born stable**; their original "same-depth gap of 0.2–3.4 Ry" is merely a **rigid
shift of the energy zero** (all 12 points offset together, within the same basin), which cancels
exactly for the curvatures C′/C44. **This establishes the health criterion as fit quality (R², number
of points dropped) rather than the raw energy gap** — the raw gap flags a harmless rigid shift as
pathological; only a *point-dependent* branch jump of the Hf kind (scattering → more dropped points /
lower R² → inflated C44) genuinely contaminates the elastic constants. The 9 alloys were merged in at
their production values, bringing the library to **1598/1598 = 100%**.

## 6. Known limitations

- **Depth mismatch for C′ in Hf-containing alloys** (C′@0.70/0.80/0.90 + B0@0.95): it originates in a
  small depth drift of the valence d band; the semi-core contribution largely cancels in the shear, so
  the magnitude is controlled but non-zero.
- The stage2 B0 of Nb-rich alloys is ~15% too soft, which propagates into their C11/C12 (see
  `stage2-summary-report.en.md` §5).
- The 12 alloys with C′≲0 are near-Bain instabilities of the **low-VEC (≤4.5) + Hf-enriched** kind
  (for the compositional pattern and the full-library test, see §4.1); they are physically sensible
  (not bad fits). Five of them (0228/0711/0945/0998/1188) only appeared once g118 revised their
  inflated C44 down to the ground-state value, revealing the real instability.

---

[^fn1963]: G. A. Featherston and J. R. Neighbours, "Elastic Constants of Tantalum, Tungsten, and Molybdenum," *Phys. Rev.* **130**, 1324 (1963). Single-crystal W at 298 K: C11 = 522.4, C12 = 204.4, C44 = 160.8 GPa.

[^hill]: R. Hill, "The Elastic Behaviour of a Crystalline Aggregate," *Proc. Phys. Soc. A* **65**, 349 (1952) (the Voigt-Reuss-Hill average).

[^pugh]: S. F. Pugh, "Relations between the elastic moduli and the plastic properties of polycrystalline pure metals," *Philos. Mag.* **45**, 823 (1954) (B/G > 1.75 counts as ductile).
