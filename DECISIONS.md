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

---

### 2026-06-15 — Gate A.2 discrimination is coarse and intrinsic → recommend demoting A.2 to corroborative

**Decision (recommendation; to strategy cross-review).** The keep-vs-demote question for Gate A.2 reduces to one measurement — its discriminating power at achievable N — now run (`verification/s0.1_gate_a2_discrimination.py`, writedown `results/s0.1_snz_triangulation/2026-06-15_gate_a2_discrimination.txt`). Recommend **demoting A.2 from a precise quantitative gate to a coarse corroborative check**, with the measured `Δ_min(N)` curve as the evidence (a finding, not a retreat).

**Why (measured, 8 seeds).** Resolution `Δ_min = 2√2·SD_seed(Δ)`: **0.49 (20k) → 0.24 (100k) → 0.12 (400k)**. Two facts: (1) `Δ_crit → 0` with N (+0.17 → +0.01) — the bias floor is dead, reconfirmed. (2) `Δ_min` is **coarse and intrinsic to separate-marginal estimation**: it's set by the **CSN marginal-exponent (`τ, α`) seed-variance**, which `(α−1)/(τ−1)` amplifies — *not* the `1/σνz` estimator. The one un-exhausted lever is a **joint `(τ,α)` estimator** (separate CSN fits leave `τ̂, α̂` ~uncorrelated — measured `corr=−0.33`, which slightly hurts); measured best case (perfect correlation) only halves the ratio SD (0.077→0.033 at 100k), still ~2× above the ~0.018 fine resolution needs, so **joint estimation is implausible to close the gap** (12 seeds; `/tmp` joint check). A.2 catches gross violations (5–10% shuffle, `V~0.2–0.5`) but cannot resolve fine near-critical distinctions (`Δ < ~0.15`) at the counts most prediction markets have (~1e3–1e5; only the largest reach 1e6).

**Consequences if adopted.** Headline criticality evidence stays `n` (the project's primary object) + Gate A.1 (CSN). A.2 reports whether the scaling relation is grossly violated, with `Δ_min(N)` stated, as orthogonal support — not a fine pass/fail. **The reference-differenced-null machinery becomes unnecessary** at this resolution (a coarse check needs no bias-cancellation to ~0.04). Pre-reg: reword Gate A.2 / H3 / §5.3 / §7 from "Δ consistent with 0" to "scaling relation not grossly violated; resolution `Δ_min(N)` reported" (a §6-plus-dependents change, Q2). Still useful but no longer blocking: a cross-class long-memory-Hawkes cell. Nothing locked; this is the measured input to the strategy cross-review.

---

### 2026-06-16 — Build-time: critical-cell Gate-A.1 failure root-caused to the GW `size_cap`, **not** the criterion (cap 1e6→1e10)

**Trigger.** Pre-certification measurement (S0.1 Task 16) found the critical G2 generator `.passes=False` on Gate A.1 at every N, failing **only** via the `truncated_power_law` LRT, with the rejection *strengthening* in N (p = 0.026→0.0006→0.00002 at N=8k→20k→40k). The spec (§149/§180) asserts the opposite ("G2 passes because no LRT favours an alternative"; "N-robust").

**Two wrong turns, then the measurement.** First diagnosis (mine) was "drop the nested `truncated_power_law` from `.passes` — it's a nested pair, `powerlaw`'s Vuong `normalized_ratio` test is invalid for it." That was an over-correction built on a **physics error**: I claimed "every finite critical system has a cutoff `s_c~1/(1−m)²`", but that is the *subcritical* cutoff and is **∞ at m=1** — an exactly-critical GW has *no* intrinsic cutoff (clean `s^-3/2`). So G2's apparent cutoff had to come from elsewhere. Measurement-before-amendment then localized it:
- **Control A** — a confirmed-clean `s^-1.5` draw (no cap) is **not** rejected by the *valid* nested test (`nested=True`, p=0.13). The test and criterion are sound.
- **The generator** — `galton_watson` carried `size_cap=10**6`; the critical `s_max ~ N^2` reaches ~10^6 at the harness counts, so the cap sat only ~1.6× above the largest avalanche and **truncated the upper tail**. Excluding the censored pile-up did *not* fix it (the tail above the cap is simply missing).
- **Control B** — raising the cap kills the rejection monotonically: cap 1e6 → REJECT (p=0.002) → 1e7 (p=0.099) → 1e8 (p=0.49, 0 censored). At 1e10, N=20000: censored=0, `.passes=True` (p_boot=0.967, no LRT favours an alternative). The valid nested test still correctly rejects the *real*-cutoff cases (subcritical m=0.7; hard-cutoff) — so it is not being blinded.

**Decision.** Default `size_cap` 10\*\*6 → **10\*\*10** (a runaway-termination safety bound only; must clear `s_max ~ N^2`, which 1e10 does for N≤~1e5). **Gate A.1's criterion and the pre-registration are UNCHANGED** — the nested `truncated_power_law` comparison stays a disqualifier (it must, to catch genuine characteristic-scale cutoffs on real data; lognormal/exponential do not reliably substitute). The §6 claim that "1e6 keeps censored <0.5% (verified)" was the trap: a *small censored fraction* (~0.1%) still depletes the tail enough to fail CSN — censored-fraction is the wrong proxy, tail-integrity is the target. Warning threshold lowered 1%→0.05% and reworded to name the tail-depletion/CSN-bias mechanism. Cost side-effect: fits now see the full tail (~8s vs ~0.8s), so the coarse gate0a cert defaults dropped to B=40/n_boot=40. Credit: the corrected diagnosis (nested-test validity + the cap suspect) came from the human reviewer; this entry records the confirming measurement.

---

### 2026-06-16 — Build-time: critical GW is Clauset-GoF-marginal → exact-power-law A.1 positive control (the Borel was never a valid one); strict-GoF-on-real-data QUEUED

**Trigger.** After the cap fix, the gate0a certification still failed: critical (and the breaker, same sizes) fail Gate A.1 — but via the bootstrap **goodness-of-fit p_boot**, not the LRT (which is clean). Measured p_boot vs N (4 seeds each): **N=5000 → 4/4 pass** (0.17–0.67); **N=10000 → 4/4 FAIL** (0.00–0.08); **N=20000 → 2/4** (passes only when KS happens to pick a high xmin). The critical-GW avalanche sizes are **Borel-Tanner** — only *asymptotically* s^-3/2, with a small (~1–4% in the pmf) non-universal bulk curvature. Clauset's GoF is strict by design (it is the test that famously rejects most empirical power laws), so once N≳10⁴ it has the power to resolve the Borel's bulk deviation and (correctly) rejects. The spec's assumption that the critical generator *passes* strict A.1 at N=2e4–5e4 was wrong — and "more N = more stable A.1" is backwards for the Borel.

**Squeeze.** Worse, the requirements conflict: critical-A.1-pass wants *small* N (≤~5–7k), but breaker-A.2-grossly-violated wants *large* N (the A.2 bootstrap half-width must drop below |Δ|). The full 2×2 closes only at N=5000, fragilely (one seed's p_boot=0.167; the breaker's Δ swings on curv-noise). Certifying there = seed/N-shopping; rejected.

**Why not an xmin floor (the seductive wrong fix).** "Impose xmin≥4 because that's where critical passes" is the refuted duration-floor wearing new clothes: choosing the analysis parameter by inspecting pass/fail on the calibration target. Fatal beyond that: a Borel-derived floor has no analytic counterpart on real Polymarket/sim data, so it would apply to the synthetic cell but not to the A.1 that runs on real data — certifying a *different gate* than is deployed. Rejected.

**Resolution (Option 3 — harness fix, no criterion change).** The Borel was never a valid positive control for "A.1 passes a power law," because it isn't one in the strict sense the gate tests. The A.1 positive control should be an **exact** power law (`generators/exact.pure_power_law`, a Zipf/zeta draw), which passes Clauset by construction. The 2×2 is re-cast as two axes: **A.1 axis** gated on strict controls (exact power law passes; subcritical cutoff `csn_killer` rejects), **A.2 axis** on the critical generator (scaling relation holds) vs the shuffle (grossly violated). With the exact control, A.1-pass and A.2-grossly-violated **both want large N** — the squeeze dissolves; cert runs at N=20000. The critical GW keeps carrying the exponents + A.2 evidence, its A.1 reported informationally (LRT-only). This changes **no registered criterion** (A.1 stays "p≥p* AND no LRT") and is spec-only (which synthetic generator is a positive control is an instrument-validation detail, not a registered hypothesis/gate). Implementation note: the positive control uses exponent **2.5, not 1.5** — a clean s^-3/2 gets KS xmin=1, so the GoF bootstrap (p_tail=1) regenerates a full heavy-tail sample and refits every replicate (intractable at N=2e4); the A.1 gate is exponent-agnostic, so a light-tailed exact power law is an equally valid control (and 2.5 is the CSN unit-test exponent).

**QUEUED for the real-data A.1-criterion cross-review (do NOT resolve now).** If the *exactly*-critical Borel fails strict GoF at achievable N because of non-universal bulk curvature, then **real critical systems — which also have non-universal bulk structure plus measurement noise — will fail strict-GoF A.1 too.** So strict-GoF A.1 deployed on real data will likely reject genuinely-critical markets/sims; this is strong evidence the strict GoF is the wrong bar for the *real-data* gate (the same shape of conclusion as the A.2 demotion). That is a real-data-gate decision, separable from the S0.1 build (Option 3 stands regardless), and it must go through cross-review with this Borel evidence **before the pre-reg freezes** — flagged and queued here, not patched. Credit: the Option-3 direction and the xmin-floor rejection came from the human reviewer; this entry records the measurements and the build change.

---

### 2026-06-16 — Build-time: recovery coverage is a calibration trip-wire (clean); full ≥0.90 certification deferred to Modal grid

**What it tests (NOT redundant with Task 8).** Task 8 verifies the profile CI is *constructed* correctly — it brackets the planted `n` on the cases tested. Coverage verifies it is *calibrated* — it contains truth at the nominal *rate* across many realizations. Distinct properties: a correctly-built interval can still be systematically too narrow/wide, and a profile CI near `n→1` is exactly where calibration drifts even when construction is fine. So coverage tests what Task 8 cannot — it is not a duplicate check.

**Result (R=30, seed 20260615, N=1e4 events; `results/s0.1_recovery/2026-06-16_coverage.txt`).** n=0.3 → 0.933 (28/30); n=0.6 → 0.967 (29/30); **n=0.9 → 1.000 (30/30)**, the near-boundary cell, `median n̂≈0.902` — no calibration drift where it was most likely. (Earlier R=12 corroboration: n=0.3, n=0.6 both 11/12.) All cells clean; none trips low.

**Honest accounting — trip-wire, not certification.** R=30 is *underpowered* for the 0.90 DoD threshold: Clopper-Pearson 95% lower bound is ~0.88 even at 30/30. So this run can rule the instrument *out* (gross miscalibration) but cannot certify it *in* at ≥0.90. Recorded as **"calibration corroborated; no sign of gross miscalibration"** — explicitly **not** "DoD met." (Overclaiming ≥0.90 from an underpowered run would be the single-seed-bias-floor mistake again.) Because all cells read clean, this does not block the S0.1 close; a low cell (8–9/12-style) would have been a finding that did.

**Deferred certification + compute path.** The full ≥0.90 grid (R≥50, all n) is deferred to **Modal CPU fan-out at S0.2** — one realization per container, which dissolves the wall hit here (8 cores × ~150s/profile-CI-fit; mp.Pool oversubscribes and neither OMP/OPENBLAS env caps nor `threadpoolctl(1)` dropped the load — it is general machine busyness, not a tunable BLAS pool). Per-fit lever tagged for S0.2: **warm-start** the profile's nuisance `(μ,β)` optimization from the previous grid point instead of cold-starting — cuts the fundamental cost threading can't touch, compounding across thousands of fits. A serial fallback in `recovery_grid` is a minor robustness add (not done; would not have scaled `make grid` here regardless). Credit: the construction-vs-calibration framing, the Clopper-Pearson honesty, and the Modal/warm-start path came from the human reviewer.

---

### 2026-06-16 — S0.4 source-A granularity: tied-time estimator fix adopted; power-law/near-critical 2 s-recovery is a blocking Stage-1 gate (qualified G1)

**Decision.** Resolve the S0.4 source-A granularity feasibility as **qualified G1** (Claude/ChatGPT cross-review; the two converged — see Status):
- **Hold the source-A build** (spike Tasks 5/6/8 — Dune fills query, `/prices-history` probe, RUN/memo). On-chain history is permanent and retro-queryable, so holding costs **no data** and removes sunk-cost pressure on the certification gate.
- **Un-hold source B** (spike Task 7, live WebSocket capture; authored + compile-checked). Its **deployment to a network agent is the time-sensitive action** — the capture is ephemeral; authoring does not start the clock. Standing up B during the spike is the registered Stage-0 task (IMPLEMENTATION_PLAN §97 pairs "prototype A" *and* "stand up B").
- **Adopt the binned/discretized-Poisson likelihood as a tied-time estimator fix ONLY**, not as a source-A verdict for the project regime. The continuous-time MLE on exact block-time ties is degenerate; the binned likelihood replaces it.
- **Book as BLOCKING gates** before any A-derived `n` enters the central claim: (i) recovery in the project regime (power-law/long-memory, near-critical) at 2 s; (ii) real-data certification.
- **Do not commit the `inf` sweep writedown as a verdict** — it is a continuous-MLE artifact (below), not a data-feasibility result.

**Why — the finding (verify-before-interpret, IMPLEMENTATION_PLAN §2).** The synthetic granularity sweep first read `T_threshold = inf` (2 s quantization appears to bias the branching-ratio estimate at every kernel timescale). Three explanations were tested and **refuted** — swept range, sample size, event rate (the un-quantized fit recovers planted `n` cleanly throughout) — isolating the cause: feeding **exact ties to a continuous-time MLE is degenerate**. The binned likelihood (the actual estimator for 2 s data) removes the degeneracy in the **resolvable** regime (kernel timescale ≫ grid: it recovers planted `n` about as well as the clean fit) and correctly fails in the **unresolvable** regime (timescale ≲ grid: within-bin self-excitation is gone). So the `inf` was **estimator inadequacy, not data inadequacy** — but the corrected result is **exponential-kernel, moderate-n**.

**Why it does not transfer — the blocking gate.** The project regime is **power-law/long-memory** (IMPLEMENTATION_PLAN §82 forbids defaulting the kernel to exponential) and **near-critical** (`n→1`). Both move toward the failure mode (scale-free kernels carry sub-2 s mass with no characteristic timescale; near-critical clustering is stronger and the MLE higher-variance). The granularity bias is **directional — upward, toward criticality** — making it a **false-positive-criticality validity threat**, not a precision problem: an under-resolved subcritical market can read near-critical, worst exactly where the margin to the critical line is smallest. Recovery must be re-tested in the target regime before A is relied on.

**Over-dispersion probe (cross-path anchor; scopes the build).** Before scoping the validation, a cheaper candidate — model the over-dispersion **marginally** (negative-binomial) rather than build a within-bin likelihood — was tested on a different code path. The 2 s-bin counts are over-dispersed (index of dispersion grows as timescale shrinks); NB's dispersion parameter converged **finite** (it genuinely fit the over-dispersion) **yet left the recovery bias essentially intact**. Diagnosis: the dropped within-bin self-excitation leaves **two distinct statistical signatures** — a marginal-dispersion moment and a temporal-order structure; `n` is identified by the **order**, not the moment. NB recovers the moment and not the order, so it fits the dispersion (its parameter converged finite) yet still cannot de-bias `n`. (Quasi-Poisson is moot: it shares Poisson's score equations for the mean, so its point estimate is identical by construction — it was never going to move.) The probe is what disproves the looser "same dropped term in two languages" reading: were they the same, fitting the dispersion would have moved `n̂`, and it did not. **Consequence:** the recovery validation is **two pieces** — a long-memory generator **and** a within-bin-marginalizing likelihood (not a count-distribution swap, not jitter's fabricated order). **De-risk order:** test the within-bin likelihood on existing exponential data first; if it cannot recover even there — and a scale-free power-law kernel carries *more* sub-grid mass, so the within-bin term is only **larger** in the target regime, making exponential-kernel non-recovery imply power-law non-recovery *a fortiori* — within-bin order is irreducible → source A is structurally inadequate in the dangerous (timescale≈grid) band → source B's sub-2 s capture becomes load-bearing (the bias lives in the channel B preserves and A's block-time destroys).

**Gate attribution — A.4 is the wrong gate.** The pre-registered **Gate A.4** (wide-CI no-interpret rule, PRE_REGISTRATION §201) is a **precision** gate — structurally blind to a directional shift that keeps the interval tight. The granularity risk is **accuracy**, so it belongs to the **Stage-1 data-validity / resolution gate**, which must test **recovery** (`|n̂−n|` across planted subcritical→near-critical) and **discrimination** (a planted subcritical value stays separable from a planted near-critical value after correction) — not CI width. The project-killing failure is the upward bias compressing the scale toward 1 so the two regimes stop being distinguishable.

**Scope boundary (named so it does not drift).** The S0.4 spike's deliverable is **this feasibility-gating finding + this decision; the spike is complete.** The recovery-validation build (two pieces) is **Stage-1's first gate, not a spike extension** — built as real `critaudit` work outside the spike firewall, never under `spike/s0.4/`.

**Status & credit.** Qualified G1 and a disciplined G2 prescribe the **identical** action list — the label is spent; the only open decision is the go on the (now two-piece) build. Cross-review convergence: Claude and ChatGPT agreed on non-transfer, the binned correction's scope, the directional risk, and the power-law gate; the live disagreement was timing, resolved to "gate before downstream investment" because the **directional** risk makes sunk-cost erosion of the certification gate the dominant hazard. Credit (per the Claude/ChatGPT/human scheme the log uses): the over-dispersion flag, the on-chain-permanence asymmetry (hold A free / start B now), and the qualified-G1 synthesis came from the Claude cross-review; the A.4 reattribution from the plan read prompted when cross-review flagged A.4 for checking; ChatGPT carried the timing call; the human reviewer-of-record orchestrated the loop and made every accept/reject call.
