# Stage-1 power-law granularity test — component certification (generator + SOE)

Per `DECISIONS.md` 2026-06-16 (qualified G1). The two foundational components for the power-law /
near-critical recovery test, each **anchored on its own output before anything relies on it**, so a
later recovery failure is attributable to the science, not an unvalidated component.

## Power-law Hawkes generator (`powerlaw_hawkes.py`)
Kernel `phi(t) = n·eps·c^eps/(t+c)^(1+eps)` (Lomax offspring delay; small `eps` = long memory, small `c`
= high sub-grid mass). Cluster/branching simulation.

**Form** — Ogata residuals via the exact Lomax compensator, indistinguishable from Exp(1) (eps=0.4,
c=0.5, n=0.6):

| statistic | value | expected |
|---|---:|---:|
| residual mean | 0.997 | 1.000 |
| residual var | 0.960 | 1.000 |
| KS vs Exp(1), p | 0.99 | > 0.05 |

**Magnitude** — the residual test shares the kernel between generator and compensator, so it is blind to
a normalization error. The horizon check disambiguates: the rate shortfall vs `mu/(1-n)` **halves as H
quadruples** → truncation (H-dependent), not a normalization error (H-invariant):

| H | rate | shortfall |
|---:|---:|---:|
| 4 000 | 0.930 | 0.070 |
| 16 000 | 0.963 | 0.038 |
| 64 000 | 0.977 | 0.023 |
| 256 000 | 0.988 | 0.012 |

→ realized kernel `n` = planted `n`. **Generator certified.**

## SOE kernel approximation (makes the likelihood O(N·M))
Built by **quadrature of the power-law's exact Bernstein representation** — well-conditioned, non-negative,
no fitting (NNLS was ill-conditioned). The far-tail quadrature deficit is absorbed into one slow component
so the branching ratio is exact. Validated on the **consumed functionals** (not just pointwise φ), across
realistic exponents at high within-bin mass:

| eps | c | F(2s) | branching ratio Σa/β (target n=0.6) | integrated kernel rel err (sub-grid) |
|---:|---:|---:|---:|---:|
| 0.4 | 0.50 | 0.47 | 0.6000 (exact) | 0.0039 |
| 0.3 | 0.25 | 0.48 | 0.6000 (exact) | 0.0039 |
| 0.6 | 1.00 | 0.48 | 0.6000 (exact) | 0.0039 |

→ **SOE certified to enter MCEM** — the consumed functionals (mass, integrated kernel sub-grid) are faithful.

## Next
SOE likelihood (O(N·M)) + MLE → plug into the validated MCEM → recovery + discrimination, sweeping the
within-bin-mass × n envelope with E-step ESS/mixing instrumented near criticality.
See `2026-06-16_recovery_verdict.md`.
