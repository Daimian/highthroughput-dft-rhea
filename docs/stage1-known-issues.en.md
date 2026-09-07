# Stage 1 fitting: record of resolved issues

English | [中文](stage1-known-issues.md)

**Final stage1 status: all 1598 / 1598 alloys fitted successfully (100%), and the retry queue is
empty.**

## The 4 formerly "unresolved" alloys (now resolved)

DFT_0470 / DFT_0933 / DFT_1421 / DFT_1259, all V-Ta-Hf-rich (V 24–40%, Ta 25–44%, Hf 15–18%).

### Symptoms

Each of them had **two electronic states** with a constant gap of **~20–24 Ry** (≈272 eV, the scale
of a semi-core state):

- the **ground state** (which has a minimum) covered 5–8 points;
- the **metastable state** (monotonic, no minimum) covered more points (6–14).

### The actual root cause (briefly misdiagnosed as a physical wall)

The initial assumption was that this needed physical tuning at the level of `setups` / the semi-core
states. Verification showed otherwise: **fitting the ground-state cluster alone already gives clean
physical results** (B0 141–167 GPa, R²≈1.0). The problem was that the **outlier energy guard** at the
time kept "the cluster with the most points", and for these four the metastable state had more points
→ the guard kept the metastable state, which has no minimum, and discarded the ground state → the fit
diverged.

Supporting evidence: 44 of the 48 alloys in the V-Ta-Hf neighbourhood succeeded, and multiple states
are very common (successful alloys often have 2–5 states as well) — DFT_0468 (Mo20V40Ta25Hf15)
succeeded while the nearly identical DFT_0933 (Ti20V40Ta25Hf15) failed, which shows this was not a
physical wall.

### The fix

The guard was changed to **keep the lowest-energy cluster among those with ≥3 points (= the ground
state)** (commit f6cea3c):

- the metastable state has more points → the lower-lying ground state is still kept (this fixes the
  four alloys);
- an isolated spurious low point (<3 points) → skipped, and the ground state is kept (which keeps
  cases like DFT_0787 working).

No recomputation was needed: 1594 → 1598.

### Lesson

Multiple states / bistability are widespread in refractory HEAs, and the correct target of an EOS fit
is always the **ground-state cluster** (the lowest-energy real electronic state), not the most
populated one. For the diagnostic scripts see `scratchpad/diag4.py` and
`scratchpad/similar_vtahf.py`.
