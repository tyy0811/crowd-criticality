# Stage-1 granularity de-risk — within-bin MCEM recovery (exponential, timescale = grid)

Per `DECISIONS.md` 2026-06-16 (qualified G1). **Question:** can the Hawkes branching ratio `n` be
recovered from 2 s block-time-quantized data by an estimator that correctly MARGINALIZES the lost
within-bin order — where the naive binned-Poisson likelihood is biased high (~0.9, even supercritical)?

**Estimator** (`within_bin_mle.py`): Monte Carlo EM. E-step Metropolis samples within-bin event
POSITIONS (counts fixed → fixed-dimension) from the Hawkes posterior; M-step is the continuous MLE. It
marginalizes the order — neither drops it (binned-Poisson) nor fabricates one (jitter).

## Result (exponential kernel, planted n=0.6, grid=2 s, horizon=800 s, ts=2 s — i.e. timescale = grid)

Target = continuous MLE on the **true un-quantized times** (the information ceiling; robust to the
MLE's own finite-sample bias). Per seed:

| seed | cont-true (target) | binned-Poisson (biased) | MCEM (n₀=0.5, below) | MCEM (n₀=0.95, above) |
|---:|---:|---:|---:|---:|
| 1 | 0.575 | 0.895 | 0.570 | 0.572 |
| 2 | 0.570 | 1.040 | 0.573 | 0.571 |
| 3 | 0.614 | 1.050 | 0.613 | 0.615 |

MCEM matches the full-data MLE **seed by seed (~0.005)**, from **both** inits — below the truth and
above the Poisson-bias attractor. binned-Poisson is off by 0.3–0.45 (supercritical at seeds 2–3).

## What this establishes
- **Within-bin order is not irreducibly required at timescale = grid:** a correctly-specified
  marginalizing likelihood recovers `n` from the 2 s counts alone, at the information ceiling. The
  binned-Poisson bias was fixable misspecification (dropped within-bin self-excitation), not lost info.
- **Init-robust:** identical convergence from n₀=0.5 and n₀=0.95 → no competing attractor at the
  Poisson-bias location → trustworthy on real data, where one cannot initialize near the truth.
- **Machinery validated separately:** at ts=16 (within-bin negligible) MCEM matched the continuous-on-
  true MLE (0.307 vs 0.310) — the augmentation is faithful.

## Scope (explicit — what is NOT shown)
- **Exponential** kernel, moderate `n`. **Not power-law** (untested; the a-fortiori runs one way only).
- **timescale = grid** (ts=2). **Not timescale < grid** (ts=1, 0.5, where binned-Poisson blew up to
  0.99, 38.8): there the within-bin window spans many kernel timescales and carries a large share of the
  signal — the harder case, untested. **ts=2 is the worst point of the *plausible-looking* band, not the
  point of maximal within-bin mass.**
- **Mechanism (why it is this clean, and where it gets hard):** at timescale ≈ grid the within-bin
  window ≈ one kernel timescale, so within-bin events are only mildly clustered and carry little
  `n`-information beyond the cross-bin/count structure; the marginalization is low-variance and MCEM
  recovers nearly everything. That is exactly why this is not yet the hard case.

## Verdict
**Bottleneck cleared on exponential at timescale = grid.** The within-bin marginalization *mechanism*
works and is init-robust. Proceed to the power-law / near-critical test (the decisive regime) per
qualified G1 — loading the high-within-bin-mass regime and instrumenting E-step mixing near criticality.
