# Stage-1 power-law granularity test — component certification (generator + SOE)

Per `DECISIONS.md` 2026-06-16 (qualified G1). The two foundational components for the power-law /
near-critical recovery test, each **anchored on its own output before anything relies on it** (review
note 3), so a later recovery failure is attributable to the science, not an unvalidated component.

## Power-law Hawkes generator (`powerlaw_hawkes.py`)
Kernel `phi(t) = n·eps·c^eps/(t+c)^(1+eps)` (Lomax offspring delay; small `eps` = long memory, small
`c` = high sub-grid mass). Cluster/branching simulation.
- **Form:** Ogata residuals via the exact Lomax compensator are indistinguishable from Exp(1) —
  mean 0.997, var 0.960, **KS p=0.99** (eps=0.4, c=0.5, n=0.6).
- **Magnitude (planted-n normalization):** the residual test shares the kernel between generator and
  compensator, so it is blind to a normalization error. The horizon check disambiguates: the rate
  shortfall vs `mu/(1-n)` **halves as H quadruples** (0.070 → 0.038 → 0.023 → 0.012 over H = 4k..256k)
  → truncation (H-dependent), not a normalization error (H-invariant). Realized kernel `n` = planted
  `n`. **Generator certified.**

## Sum-of-exponentials kernel approximation (makes the likelihood O(N·M); review note 2)
Built by **quadrature of the power-law's exact Bernstein representation** `phi(t)=∫rho(s)e^{-st}ds`,
`rho(s)=n·eps·c^eps/Gamma(1+eps)·s^eps·e^{-sc}` — well-conditioned, non-negative, no fitting (NNLS was
ill-conditioned). The heavy far-tail (small-s) quadrature deficit is absorbed into one slow component
so the branching ratio is exact without perturbing the sub-grid integral.
- Validated against the **consumed functionals** (not just pointwise φ), across realistic exponents
  (eps = 0.3 / 0.4 / 0.6, c = 0.25 / 0.5 / 1.0, all at high within-bin mass F(2s) ≈ 0.48):
  - **branching ratio** (total mass `Σ a/beta`): **exact** (rel err 0.0000) — the quantity a recovery
    bias would flow through.
  - **integrated kernel / compensator** (the MCEM-consumed functional): **0.4%** rel err, sub-grid and
    bin-integrated.
- **SOE certified to enter MCEM.**

## Next
SOE likelihood (O(N·M) recursion) + MLE; plug into the validated MCEM framework; **recovery +
discrimination** (planted 0.6 separable from 0.95) **sweeping the within-bin-mass × n envelope** (not a
single point — review forward note), with **E-step ESS / mixing instrumented near criticality** (a
poorly-mixed sampler can look converged and be wrong).
