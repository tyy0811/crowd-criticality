# DECISIONS.md

Append-only design-decision log. Each entry: the choice, the *why*, and (where it matters) the measurement or rule that fixed it — never a result (`n`, an exponent, or a Brier number). New entries go at the bottom.

---

### 2026-06-15 — Wrap `powerlaw`, build the Hawkes MLE ourselves

**Decision.** CSN power-law fitting wraps the `powerlaw` package (Alstott et al.); the exponential-kernel Hawkes MLE is built in-house (Ogata recursive log-likelihood + `scipy.optimize` + time-rescaling residuals).

**Why.** In-environment probe (not assumption): `powerlaw` 2.0.0 has a clean `py3-none-any` wheel; `tick` has **no** wheel for this platform/Python and would compile its C++/SWIG core from source against **numpy 2.0.2** (a 2021-era package two major numpy versions behind). Putting a fragile source build under the dependency root of the whole repo is the larger risk; the exp-kernel MLE is small and gives full control of near-`n→1` behavior and residual diagnostics. Reimplementing CSN, by contrast, would only add correctness risk against a reference, with no upside.

---

### 2026-06-15 — Ground-truth generators live in `critaudit.generators`, not top-level `synthetic/`

**Decision.** The synthetic generators are part of the installable package; top-level `synthetic/` is the run-and-writedown location only.

**Why.** `critaudit` detaches as a standalone toolkit; its generators are its validation surface and must ship with `pip install critaudit` so any downstream user — including the later scale-free imaging/PET work that is the reason it detaches — can validate their own pipeline against the same ground truth. (Deviation from the IMPLEMENTATION_PLAN §1 tree, which placed `synthetic/` at top level.)

---

### 2026-06-15 — `n` confidence interval: profile-likelihood primary; bootstrap as method-transfer audit

**Decision.** The MLE is stationarity-unconstrained (`n̂` may exceed 1). Primary CI is profile-likelihood (asymmetric, upper limit free). Wald/Fisher is rejected. A parametric bootstrap runs only at the `n=0.99` cell, and its role is **method transfer**, not calibration.

**Why.** The pre-registration treats `n≥1` as a reportable outcome, so a symmetric Wald CI is the wrong shape at the boundary; the audited near-critical failure mode is variance inflation from a flat likelihood, not boundary non-regularity (no `n<1` constraint ⇒ no Chernoff-type χ² breakdown). Coverage-vs-ground-truth already certifies whether profile is honest, so the bootstrap is not a calibration check; its job is to confirm profile↔bootstrap agreement at the boundary, because bootstrap is the CI that carries to truth-free real data in Stage 1.

---

### 2026-06-15 — Parallelize across realizations with `multiprocessing`; no `numba`

**Decision.** The estimator-recovery grid parallelizes across (embarrassingly parallel) seed-spawned realizations via `multiprocessing`. The per-fit Ogata recursion stays sequential pure-Python-on-numpy. `numba` is not adopted.

**Why.** `numba` is the same build-fragility class as `tick` — it lags numpy releases, and numba-on-numpy-2.0.2 in mid-2026 is a probe-before-depend question. Multiprocessing reaches the needed throughput with no fragile dependency.

---

### 2026-06-15 — Phase-1 / Phase-2 firewall enforced by separate spec files

**Decision.** S0.1 is split into a fully-detailed Phase-1 spec (instrument core = Gate-0(a)) and a Phase-2 robustness stub marked "do not start until Gate-0(a) passes." Phase-1 retains the forward interfaces (joint-bootstrap signature, `gate_a2` ceiling hook, generator knobs, reserved `marks` field) because they constrain Phase-1's API.

**Why.** A file boundary is an enforceable scope gate for an agent build; one document with a detailed Phase-1 beside a sketched Phase-2 invites starting Phase-2 stubs before the instrument is validated — the exact thing the firewall exists to stop. Phase-2 is a Stage-1 prerequisite (fitting real data honestly), not a Gate-0(a) prerequisite.

---

### 2026-06-15 — Phase-1 Gate-A.2 uses the ceiling-free sign test; the near-critical cell is characterized, not gated

**Decision.** `gate_a2.classify(..., ceiling=None)` runs only the sign test in Phase 1 (G2 → "not-inconsistent"; scaling-breaker → "inconsistent"). The `n=0.99` recovery cell is characterized (coverage, CI width, profile↔bootstrap agreement) and handed to S0.2 rather than gated.

**Why.** The consistent/inconclusive trichotomy needs the Gate-A.2 informativeness ceiling, which is an S0.2 deliverable that does not exist at Phase 1; importing it would break the firewall and the result-blind discipline. The sign test is the N-robust, calibration-independent part — exactly the property claimed for the Gate-0(a) harness. The near-critical floor is S0.2's actual object of study, so Phase 1 must not pre-empt it.
