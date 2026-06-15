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

---

### 2026-06-15 — Pre-plan verification: `1/σνz` fit floor at duration `x_min`; brentq profile CI; critical cell needs adequate avalanche count

**Decision.** Before writing the implementation plan, the riskiest algorithms were measured in-environment (verify→fix). Three operationalizations were fixed as a result:
1. **`1/σνz` is the `log⟨S|T⟩`-vs-`log T` slope fit with its lower range floored at the CSN-selected *duration* `x_min`** (not `T=1`), excluding censored avalanches.
2. **The profile-likelihood CI for `n` uses `brentq` root-finding**, not a grid scan.
3. **The Gate-0(a) A.2 cells run at `≈5×10⁴` avalanches** with `size_cap=10**6`.

**Why (measured, not assumed).** The exponential-kernel Ogata-recursion MLE recovers planted `n` essentially exactly (`n̂ = 0.286/0.577/0.900` for `n = 0.3/0.6/0.9`), and the `powerlaw` package API was confirmed. But the crackling-relation discrepancy `Δ` for a *genuinely critical* generator came out `≈0.55` (joint-bootstrap CI **excluding 0** — a false negative) with a naive `T=1` slope floor at `≈8×10³` avalanches. The cause is small-`T` curvature in `⟨S|T⟩` plus finite-sample exponent bias, **not** the size cap (slope unchanged at cap `10⁶`). Flooring the slope fit at the duration `x_min` and raising the count to `≈5×10⁴` gives `τ≈1.50, α≈1.95, 1/σνz≈1.84 → Δ≈0.06` (CI contains 0). Separately, a 200-point pure-Python profile scan was untenable (≈40k sequential recursion passes); brentq needs ≈30 profile evaluations.

**Effect.** Updated the S0.1 spec §§3, 4.1, 4.2, 4.4, 5. The instrument as *originally* specified (naive `1/σνz`, unstated count) would have failed Gate-0(a) on its own critical generator — caught here, before any plan or compute, which is the entire point of the S0.1 slice. The fit-floor rule is result-blind (duration `x_min` is KS-selected on the marginal, never inspects `Δ`/`n`). Flagged to the owner for cross-review as a Gate-A.2 operationalization that the frozen pre-registration's §5.3/§6 should reflect.

> **SUPERSEDED in part by the next entry.** The owner's review flagged that *choosing the duration-`x_min` floor because it drove G2's Δ→0* is Δ-tuned at rule-selection time — result-blind at evaluation but not at selection. The mandated verify-then-fold anchor check then **refuted** the floor. The `brentq` CI, the censoring/`size_cap`, and the `AvalancheSet.censored` field below all stand; only the `1/σνz` fit-floor rule is withdrawn.

---

### 2026-06-15 — Anchor check REFUTES the duration-`x_min` floor; `1/σνz` estimator reopened (Gate-A.2 blocker)

**Decision.** Withdraw the duration-`x_min` fit-floor rule. Do **not** fold it into the pre-registration. The `1/σνz` estimator is an **open S0.1 design question**; the leading replacement is the **avalanche-shape-collapse estimator** (Friedman et al. 2012), to be verify-then-locked before the scaling module, the §5 critical cell, plan Tasks 10–11, or the pre-reg are finalized.

**Why (the free anchor check the owner mandated — establish the true scaling-regime onset from huge-N ground truth, with no reference to any `x_min` or to `Δ`).**
1. **No onset exists to anchor to.** The `⟨S|T⟩` local slope climbs monotonically (1.73→1.88) with no plateau at reachable `T`; "floor at the onset" has no referent.
2. **The CSN duration `x_min` is noise, not an onset:** 21 / 31 / 11 across N = 20k / 50k / 100k (non-monotone, unstable).
3. **The binned-slope estimator is biased low even asymptotically** — `(α−1)/(τ−1)=1.97` vs huge-N slope `≈1.86`; the gap is comparable to the `Δ` being resolved.
4. **The failure is point bias, not CI width** (per-replicate / honest bootstrap): naive `Δ_point=0.25`, CI `(0.14,0.46)`, halfwidth `0.16` at N=5×10⁴ → CI excludes 0 because the point is biased.
5. **The floor is operationally brittle:** at the harness N the selected floor (`x_min≈31`) leaves too few duration bins above it to fit the slope (the check crashed there).

**Root cause of my error.** I selected the duration-`x_min` floor *because it made the known-good (critical) case pass* — structurally identical to over-fitting the calibration target. Each component (KS `x_min`, S0.2 count) is result-blind, but the *choice among candidate floors* was `Δ`-guided. Result-blind components do not compose into a result-blind rule for free.

**Margin-safety (deferred, noted):** even a corrected estimator's *false-positive* safety — that it still **rejects** a small-`Δ` mismatch generator — must be certified against that generator, which lives in **S0.2**. So the estimator cannot be fully margin-certified from S0.1 alone.

**Effect.** Backed the floor claim out of spec §4.4 and §5 (estimator marked OPEN; critical A.2 cell reported blocked/inconclusive). Plan Tasks 10–11 (binned-slope estimator) are not finalizable until the estimator is resolved. Nothing folded into the pre-registration. No pre-reg §10 entry (draft is unfrozen; §10 is for post-freeze deviations).

---

### 2026-06-15 — `1/σνz` estimator triangulation: `curv` recommended primary, `tail` robustness, shape-collapse dropped (pending cross-review)

**Decision (recommendation, not yet locked).** Per the estimator-triangulation norm (plan §2.5), ran a set of `1/σνz` estimators chosen to fail differently through identical gates on Galton–Watson ground truth (evidence: `verification/s0.1_snz_estimator_triangulation.py`, writedown `results/s0.1_snz_triangulation/2026-06-15_writedown.txt`). Recommend **`curv`** (curvature-corrected bulk fit `log⟨S|T⟩ = a + γ logT + b/T`, lowest DOF) as **primary**, **`tail`** (large-`T` OLS, opposite data region) as **robustness/triangulation partner**, and **drop avalanche shape-collapse**.

**Why (measured).** Selection criterion was pre-committed and result-blind: point → known `2.0` AND CI tightening; look-alike rejection; mutual agreement.
- **Shape-collapse (highest DOF, the literature favorite) failed:** stuck at `1.650` across N (Δ growing 0.17→0.30, no convergence) and **structurally unable to reject** the S–T-shuffle look-alike (it reads the profile, not `S`). Verifying it alone would have locked the weakest estimator — the same single-favorite error the binned floor was.
- **`curv` (lowest DOF) passed:** estimate rises `1.79→1.87` toward 2, Δ-CI contains 0 at all N with half-width tightening `0.22→0.13`, rejects the look-alike (Δ≈3.1). Adding one curvature term lifts the binned estimate `1.71→1.88`, **confirming** the binned failure was unmodeled small-`T` curvature.
- **`tail` agrees** with `curv` to 0.002 at 100k (1.867 vs 1.869) from the opposite data region → real triangulation; rejects the look-alike.

**Caveat (load-bearing).** Even the best estimators plateau near `1.87`, not `2.0`: the Δ *point* sits at `≈0.09`, flat across N, masked by CI width. A genuinely critical generator gives Δ≈0.09, not 0. This constrains **S0.2**: the Gate-A.2 informativeness ceiling cannot be set below ~0.09 without making a true critical generator read "inconclusive." Chasing the residual to 0 by adding correction terms is the DOF-tuning trap and is refused.

**Sequencing.** This comparison is the **input to the Claude/ChatGPT cross-review** (owner-run); the estimator is **not** locked into spec §4.4, plan Tasks 10–11, or the pre-reg until cross-review confirms. Small-Δ margin-safety certification is an S0.2 deliverable.

---

### 2026-06-15 — Gate A.2 null must be the synthetic-critical reference, not Δ=0 (bias-floor flip; reference-differenced gate verified)

**Decision (recommendation, pending cross-review).** Reformulate Gate A.2's null: **"consistent" ≙ the test system's Δ matches the *same estimator's* Δ on a matched synthetic-critical reference**, not "Δ-CI contains 0." Evidence: `verification/s0.1_snz_reference_gate.py`, writedown `results/s0.1_snz_triangulation/2026-06-15_reference_gate.txt`.

**Why (the owner's catch, then measured).** The residual Δ≈0.09 from the triangulation is a *bias floor*, not a width artifact, and "contains 0" is fragile to it. Pushing N past 100k showed the two estimators behave differently: **`curv` slowly converges** to 2 (1.865→1.929 over 100k→800k; benign), but **`tail` floors at ~1.874** (Δ floors at ~0.126, never shrinks). A floored estimator's Δ-CI **excludes 0 once the CI tightens below the bias** → a *genuinely critical* system reads "inconsistent," a false rejection that **worsens with data**, exactly in S0.2's large-N regime — and the informativeness ceiling cannot prevent it (it governs consistent-vs-inconclusive, not "excludes 0"). So Δ=0 is the wrong null: with a biased-but-consistent estimator the right empirical null is the estimator's *measured* Δ on a matched critical reference.

**Verification (N=250k, past tail's flip).** Under the OLD gate both critical-test systems are falsely rejected (CI excludes 0). The reference-differenced gate (`Δ_test − Δ_ref`, same estimator) returns **consistent** for both (δ-CI tight around 0, ±0.04) and **rejects** the look-alike (δ-CI far from 0: +3.4 curv, +1.9 tail). The common bias differences out; the shrinking CI becomes a confidence feature; discrimination is preserved (sharpened). Robust to estimator bias-behavior and to the `x_min` choice.

**Effect.** This is the anchor check for a pre-reg **§6 reformulation** ("Δ consistent with 0" → "Δ consistent with the matched synthetic-critical reference"). Gate-D-clean: the reference is calibrated on the synthetic critical generator only, never on the real/sim test Δ or n. **Not locked** — it is the corrected, fully-characterized input to the Claude/ChatGPT cross-review (Step 3). Build execution remains parked; the fourth-estimator idea is dropped (three agreeing to 0.002 is sufficient triangulation; a fourth does not touch the bias floor).

> **SUPERSEDED by the next entry.** A 5-reviewer adversarial round + owner re-verification overturned the bias-floor premise of this entry and the fairness of the shape-collapse drop.

---

### 2026-06-15 — Adversarial round overturns Findings 2 & 3; Gate-A.2 estimator/null analysis must be redone (nothing was locked)

**Decision.** Withdraw the "bias floor → reference-null" conclusion (the entry above) and the "shape-collapse measured worst" conclusion (the triangulation entry) as **not earned by the evidence**. Hold Q2 (no §6 freeze) firmly. Q1 is **not blessable** as written. The Gate-A.2 estimator selection and gate-null require a proper redo. Evidence: `verification/s0.1_snz_redo_diagnostics.py`, writedown `results/s0.1_snz_triangulation/2026-06-15_adversarial_verification.txt`.

**Why (5 blind adversaries; owner re-verified the two most damaging claims).**
- **The Δ≈0.09 bias floor was largely single-seed noise + a `1/T`-form choice.** Across 6 seeds, curv's Δ = +0.029 (100k) / +0.018 (200k), consistent with 0; my reported 0.09–0.13 were high-ratio seed draws (13, 21). The marginal ratio is itself ~1.90, not 2.0, at these N. So **Finding 3's premise collapses** — the reference-null solved a problem that mostly isn't there at achievable N.
- **Correction form is a 0.47-wide DOF; AIC prefers `1/√T` (γ=2.07), but that makes the relation FAIL (Δ=−0.16)** because the CSN ratio is finite-size-biased to ~1.90. The relation closes via *mutual* bias consistency, so selecting the estimator by "it closes Δ" is the Δ-tuning trap one level up. **The principled estimator-selection rule is unresolved.**
- **Shape-collapse was dropped on a biased objective** (shipped relative-CV stuck at 1.65; standard objective 1.82, peak-height 1.90). **Finding 2 was unfair.**
- **Standing logical objections:** discriminating power was tested only on the trivial full-shuffle (small-Δ rejection deferred while "verified" was claimed); the Δ=0-achievable assumption contaminates H3/§5.3/§7/§4f, not just §6; the reference-null adds DOFs and may not transfer to real (non-GW, long-memory-Hawkes) data; B=25/50 bootstraps flip verdicts ~20–35% on seed.

**Effect.** No artifact damage: nothing was locked or frozen; the flawed conclusions lived only in this DECISIONS trail and the spec kept the estimator OPEN. The adversarial round caught it before any lock — the intended function. Next: a consolidated redo (multi-seed; B≥500; correction-form envelope with a pre-committed form or a physics justification for `1/T` over `1/√T`; fair shape-collapse with a standard objective; a small-Δ genuine-violation discrimination cell; a non-GW critical reference cell for transfer) before cross-review can reconsider Q1. The reference-null may still earn a place on the truth-free-real-data argument alone — but not on the bias-floor motivation, which is withdrawn.
