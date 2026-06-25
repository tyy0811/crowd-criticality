# tradeoffs.md

Methodology lessons from checks that fired. Each entry: what the check found, the root cause, the fix,
and what the cost would have been if the check hadn't existed. (Per the pre-flight discipline in
~/.claude/CLAUDE.md: "If a check fails, write a tradeoffs.md entry after fixing it.")

---

## 2026-06-24 — Increment 3: the gate was fitted on an out-of-calibration horizon (uncensored offspring)

**What the check found.** The two-pass review (dynamic-workflow `/code-review` + Codex adversarial) of the
classical-ABM shakedown flagged that `sim/controls/deffuant._grow_tree` appended every offspring event
unconditionally, dropping the `if ct < horizon` truncation its mirrored reference
(`generators/powerlaw_hawkes.simulate_labeled`, line 89) applies to every child. A direct measurement
confirmed the consequence: with the frozen infinite-mean Lomax kernel the HIGH (deep-supercritical) plant
put **92.7%** of its N-matched window past the nominal horizon, and `run_pipeline` handed the μ(t) gate an
effective horizon of **~6.6e7** (≈16,000× the drive horizon of 4000) — i.e. the gate was read entirely
outside the finite-window, heavy-tail-truncated process class it was calibrated on. The first (uncensored)
discrimination "passed" only because that ballooned window let the smeared cascade reach the n-grid ceiling.

**Root cause.** A missing finite-observation-window model. No real crowd is observed over an infinite
window; the uncensored generator silently modelled an infinite-duration observer, and with infinite-mean
delays that manufactures an unbounded horizon from a bounded drive. The spec's own "substrate consistency"
claim (the gate operates on its calibrated process class) was thereby false for the near-critical and
supercritical plants.

**Fix.** Censor offspring at the `horizon` variable in `_grow_tree` (same gate as the reference). A SECOND
review pass refined the censoring semantics: only an OBSERVED (in-window) firing marks an agent refractory
— a censored offspring keeps its success/opinion-update (the interaction happens at the in-window parent
firing, so n_tree stays a local per-firing ratio) but is NOT activated, so a censored FUTURE activation can
no longer suppress an earlier in-window one. That suppression was a **favorable-direction** bias (it
undercounted in-window events → biased the gate peak DOWN → flattered HIGH toward subcritical, ~0.45 vs the
faithful ~0.6); fixing it banks the less-flattering number. The fix keeps the reference's generation-order
queue (NOT chronological — a time-ordered queue would make the control more physically faithful than the
process it controls for, reintroducing a control-vs-reference difference). The honest consequence — logged
not relaxed — is the actual finding: under finite-horizon observation the gate's *observational* branching
ratio is regime-blind (the deep-supercritical HIGH plant reads subcritical, ~0.6 < 1, while structural
n_tree holds it ~3.1), and only the local structural anchor n_tree resolves regime. (Third measured
instance of heavy-tail temporal-non-compactness, after the cascade-#3 block.)

**Cost if the check hadn't existed.** The increment would have shipped a headline "the pipeline
discriminates subcritical from supercritical" that was an artifact of an unphysical infinite observation
window — a wrong methodological claim folded into the Stage-2 control arm, propagating into the LLM-sweep
design that builds on this gate. The real, opposite finding (the gate cannot read supercriticality under
the project's own heavy-tail kernel) would have stayed invisible behind a green @slow test.

---

## 2026-06-24 — Increment 3: χ (var of population-mean opinion) is not a susceptibility

**What the check found.** The result-blind secondary criterion — a susceptibility should PEAK at
criticality, `chi(CRIT) >= chi(LOW)` and `>= chi(HIGH)` — did not clear: measured χ did not peak at the
critical plant. A controlled sweep (mu_news held FIXED, eps swept across criticality, multiple seeds;
`results/s2_shakedown/2026-06-24_chi_diagnostic.py`) confirmed χ is flat-to-noisy in eps with no resolved
peak at eps_crit (chi(crit)/mean(others) ≈ 0.98 — eps_crit below the mean).

**Root cause.** χ was defined as the temporal variance of the population-MEAN opinion. The mean is ~0.5 by
the symmetric Deffuant dynamics — it is not an order parameter, so its variance is not a susceptibility and
carries no critical signal. (The cohort comparison was additionally confounded by the three plants using
different mu_news, so the belief trajectory had very different sample counts.)

**Fix.** Converted the failed criterion into a passing characterization (`test_chi_has_no_resolving_power`)
that asserts the robust no-peak from the controlled fixed-mu_news sweep — NOT relaxed to pass. The
assertion rests on the controlled sweep ONLY: a tempting single-cohort secondary (`chi(CRIT) < mean(chi(LOW),
chi(HIGH))`) was tried and **dropped** when the 2nd-review 20-seed probe measured it failing 5/20 — a fresh
point-inequality knife-edge on a noise-dominated quantity, exactly the failure mode being characterized. χ
stays demoted to a noisy non-anchor; a future sweep needing a critical-point locator must redefine χ (e.g.
cross-agent opinion dispersion), not use var(population-mean). The primary anchor n_tree (monotonic, crosses
1) is what orders the plants.

**Note on a superseded fix.** An interim characterization asserted a HIGH-collapse (`chi(HIGH) << others`).
That collapse was itself an artifact of the *pre-fix* configuration (uncensored giant cascades + a 60-sample
low-budget belief regime); under the corrected-and-budgeted configuration it is gone (χ is uniformly noise
across all three plants). Measurement-before-amendment overturned the interim assertion — the no-peak claim
is therefore sourced from the controlled sweep, not from any cohort-specific χ ordering.

**Cost if the check hadn't existed.** χ would have been carried as a working susceptibility/critical-point
locator into the §4f sweep, where it would have been used to locate criticality it cannot actually locate —
a silent dependency on a noise-only observable.
