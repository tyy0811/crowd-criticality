# Causal probe — pre-authorization writedown (Tasks 3–7C + owner-review repairs)

**Dates:** 2026-07-22 (Tasks 2C–7C, nine commits `4e8a77b..a054868`) and 2026-07-23 (owner-review repairs, commits `de550cb`, `f43a915`, `f033ab1`, plus this writedown update) · **Branch:** `stage2-causal-probe-freeze` · **Plan:** `docs/superpowers/plans/2026-07-22-oasis-causal-probe.md`
**Freeze commit:** the commit introducing this writedown update completes the repaired executable freeze; the final HEAD is recorded in the Task-8 handoff.
**Status: pre-authorization. The Task-8 owner stop is binding. No scientific, LLM, GPU, or provider-backed run has occurred or is authorized by anything below.**

## 0. Owner review 2026-07-23 — six findings, all repaired

The first Task-8 handoff (at `a054868`) was rejected with six findings; each was verified against the code and repaired test-first:

1. **`--execute` did not enforce the banked hashes before its first draw** → `--execute` now requires the banked dry-run manifest file (written by `--dry-run`); the frozen frame hash is checked against it up front, a dedicated pre-draw verification session must recreate the banked eligibility-evidence hash before any draw anywhere, and every live session enforces the same evidence hash pre-draw inside the bridge (`f033ab1`).
2. **The gate could PASS forged or missing structural evidence** → the gate now re-verifies every structural claim from primary evidence: complete run ledgers re-estimated through the production estimator, byte-hash chains against the banked manifest (frames reconstructed from canonical bytes and round-tripped), marker cells re-aggregated, and the chi peak re-located; forgery or absence raises, and `structural_failures` is 0 by construction whenever the gate returns (`f033ab1`; forgery power checks in `tests/test_causal_probe_runner.py`).
3. **Refresh isolation had a fail-open case** — an organic refresh at an unregistered round could serve a registered recipient its future experimental parent with no guard → `assert_no_pending_exposure` on the controller, routed through the platform wrapper for every unregistered refresh (`de550cb`).
4. **The power simulation and execution used different joint randomization laws** → power is re-banked as the probability that the gate's own statistic (per-cell mean of 12 single-realization estimates on freshly drawn schedules) passes the scientific clauses, computed exactly via sufficient statistics and cross-checked against an independent brute-force replay of the joint law (`f43a915`; §2).
5. **Generator truth was absent from the future result artifact** → the execute artifact now records `R_plant`, hidden `R_gen_frame`, and the canonical potential-response-schedule hash per run, in the artifact only — never in the gate's inputs (`f033ab1`).
6. **Commit count** — the first handoff claimed ten commits for Tasks 2C–7C; the correct count was nine. Corrected here and in the handoff.

## 1. What was built (Tasks 3–7B)

- **Task 3** (`6529ed2`): pure fixed-frame `CausalRefreshController` — exact categorical selection over registered pair probabilities plus the residual no-selection mass, treatment at exactly 0.5 only on selection, one immutable `StratumDraw` per stratum, per-refresh frame re-hash, symmetric parent/filler serving in the first feed slot with length preservation, fail-closed on unknown/duplicate/missing/out-of-order strata.
- **Task 4** (`d274580`): installed-OASIS integration. `apply_causal_refresh` delegates ordinary refresh construction to the production `Platform` and re-records the refresh trace so served IDs always equal the returned feed; `load_frame_eligibility_evidence` measures author/creation-round/first-readability/prior-exposure/opportunity from actual DB+trace rows; `collect_causal_outcomes` joins exactly one fail-closed outcome per assignment on native links only (no text inference); `run_oasis_minimal` gains both-or-neither `causal_frame`/`causal_controller` hooks with a byte-equivalent inert default (default exporter untouched; regression pinned).
- **Task 5A** (`3483d08`): scripted one-generation control with planted truth — fixed pre-selection potential responses, `R_plant = mean_parent(sum q)`, hidden `R_gen_frame = mean_parent(sum y)`, holdouts never reply — plus the full-platform non-LLM bridge (`run_scripted_oasis_control`) on the production wrapper/selector/estimator with the fail-closed sentinel model.
- **Task 5B** (`e4c6cb3`): disjoint recursive marker control for `chi_resp` as native quote cascades (readable r+1 horizon, equal registered support, marker-namespaced IDs, rounds offset to 2+), `CV²` pooling with equal root weight (6,144 concatenated sizes; seed-level averaging structurally impossible), and `locate_chi_peak` requiring an interior unique aggregated maximum with 12/12 seed-argmax consistency.
- **Task 6** (`b3e8f2f`): AST import firewalls (no similarity/powerlaw/Hawkes/parrot/`n_resp` in any causal module; estimator import surface pinned to records/validators/spec/math), field-by-field manifest disjointness guards with one-field-overlap power checks, `require_disjoint_seed_sets`, known violators (dropped no-selection draw, smuggled pair, denominator reconstruction, frame-hash change, duplicate native child), and the strict validator suite passing under both normal Python and `python -O`.
- **Task 7A** (`232b404`): result-blind constants frozen before generation (coverage ≥ 0.95, mean full width ≤ 0.10, power ≥ 0.80, 200k replicates, Wilson-99% half-width ≤ 0.003, seed registries pairwise disjoint); exact-selector Monte Carlo via the sufficient statistic `K = Bin(M1, 0.2) + Bin(M2, 0.4)` (the exact law of the frozen selector; power-checked in-tests against an independent per-stratum replay); banked artifact reproduces byte-identically.
- **Task 7B** (`14fc14a`): dormant recoverability runner — frozen gate clauses, canonical manifest, `--dry-run` hash preflight through root creation only, `--execute` guarded behind the Task-8 owner stop and reachable only through the scripted and marker controls (no provider/LLM import surface; AST-pinned).

## 2. Power freeze (banked, $0; re-banked 2026-07-23 under the aligned law)

- Artifact: `results/s4_causal_probe/2026-07-22_power_calculation.json`
- SHA-256: `b4091ab19cbffc90b6e508b9495fc147ad5a23e24b001148aa245054f63db660` (frozen in `causal_probe_spec.py`; byte-reproduced after re-banking)
- **Aligned joint law (review F4):** banked power is the probability that the gate's own statistic — the per-cell mean of 12 SINGLE-realization estimates on freshly drawn potential-response schedules — passes strict ordering, exactly-one-crossing, and the near-crossing error bound, under the exact frozen selector. Computed via sufficient statistics (per-stratum live counts Multinomial, included counts Binomial) at 200k grid replicates, cross-checked in-tests against an independent brute-force replay. Schedules for the power computation come from a dedicated stream; the held-out recoverability registry is never inspected (AST-enforced).
- **Selected support: 8192 parents × 4 recipients (32,768 pairs; 16,384 strata) — unchanged by the re-bank.** First candidate in the frozen order to pass every cell: worst-cell mean full CI width 0.099 (plant 1.30) vs the 0.10 ceiling; coverage ≥ 0.95 in all six cells; aligned-law power 1.000 (all three clause rates 1.000; Wilson half-width 1.7e-5); zero structural failures. All 23 smaller candidates fail the width criterion (measured, recorded per cell in the artifact). The pre-repair fixed-schedule cohort diagnostics remain in the artifact as descriptive records under `fixed_schedule_cohorts`.
- Deterministic worst-case variance bound imported from the production estimator (never reimplemented).

## 3. Full-scale dry-run preflight (measured)

- Command: `python -m critaudit.experiments.causal_probe_recoverability --dry-run --power-artifact results/s4_causal_probe/2026-07-22_power_calculation.json`
- Banked dry-run manifest SHA-256 (2026-07-23, post-repair): `3553d9467edef2bf5fd3bee67da5ee46d0cd93801abc1cfe47f0d9092b0f4d42` — the canonical manifest file is now WRITTEN by `--dry-run` (`dryrun_manifest.json`; durable copy at `~/crowd-crit-runs/s4_causal_probe/2026-07-23_dryrun_manifest.json`).
- Frame SHA-256: `045bd40c8d36cbebe642c613de484ab439e7607a9d3de61e4235866836b63182`
- Eligibility-evidence SHA-256: `9980fbc145d5deb293ae982c2426eadbd5438e01beaf97ab70680db073b2556f`
- The frame and evidence hashes reproduced **byte-identically across two independent full-scale dry-runs** (2026-07-22 pre-repair and 2026-07-23 post-repair); the manifest hash changed only because it embeds the re-banked power-artifact hash.
- Wall time: ≈ 44 minutes per full-scale dry-run at the selected support (24,578 sign-ups; 16,386 reply-layout posts; canonical evidence over 32,768 pairs; 512 marker roots). Teardown before any draw, verified in the pre-draw databases both times: 0 refresh trace rows, 0 comments, no result artifact.
- **Execute-side enforcement (review F1):** `--execute` now REQUIRES `--manifest <banked dry-run manifest>`; it checks the frozen frame hash against the manifest up front, recreates the banked evidence hash in a dedicated pre-draw verification session before any draw anywhere, and enforces the same evidence hash pre-draw inside every live session. **The plan's registered Task-8 command therefore needs `--manifest` appended at authorization time — an owner amendment to the plan text, flagged here rather than made unilaterally.**

## 4. Wall-time forecast for the Task-8 grid (measured basis — owner decision input)

The installed OASIS `Channel.read_from_send_queue` polls its response dictionary at a fixed 0.1 s sleep, so every platform action costs ~0.05–0.1 s of latency, and the concurrent sign-up phase additionally burns CPU quadratically in pending pollers. Measured at the selected support on this machine:

- sign-ups: 24,578 agents in ≈ 14 min (≈ 29/s under the concurrent gather);
- sequential creations: ≈ 10 posts/s (measured 591/min mid-run).

Per reply session forecast (sign-ups + 16,386 creations + 16,384 refreshes + up to ~2.1k scripted replies + evidence): **≈ 70–80 min**. The registered grid is 6 plants × 12 seeds = 72 reply sessions plus 72 marker sessions (≈ 3–6 min each):

- **Total forecast: ≈ 90–100 hours (≈ 4 days) of continuous wall time. $0 in API/GPU/provider cost.**

This forecast is a substrate-latency fact (the channel's polling design), not a scientific gate. Whether ~4 days of unattended wall time fits the ratified budget gate is an **owner call at Task 8**; the alternatives (patching the channel's poll interval, sessionizing differently, or treating the cost as a budget-gate failure → Branch B) all require ratification and are **not** exercised here.

## 5. Verification state (post-repair)

- Whole-repo non-slow suite at the repaired tree: **521 passed, 2 registered skips, 44 deselected slow** (`pytest -q -m "not slow"`), `git diff --check` clean. Focused 12-file causal battery: **326 passed**.
- The focused causal battery now includes the gate forgery power checks (six forged/missing-evidence variants each raise), the bridge banked-evidence enforcement (a wrong hash fails closed before the first draw, verified against the session database), the pending-exposure isolation guard, the canonical frame/manifest byte round-trips, and the brute-force cross-check of the aligned power law.
- Whole-branch review (Task 7C, pre-repair) found and fixed three defects pre-commit (power-artifact path resolution off by one directory; a weaker cross-session evidence guard, since superseded by banked-hash enforcement; cohort alignment by index rather than schedule seed). The 2026-07-23 owner review found the six findings in §0; all are repaired and test-locked.

## 6. Boundaries (unchanged)

`R_reply` is a one-generation design estimand on the fixed scripted operator; it is **not** Hawkes `n`, activates no H1b claim, and authorizes no sweep, Stage-3 work, or OASIS LLM run. The observed diagonal variance output remains `estimated_diagonal_variance_bound` with `design_only` status. Branch B remains the mechanical fail branch, verbatim:

> Bank that no recoverable OASIS regime instrument is available; retain the classical locator and OASIS accessibility findings; restrict future analysis to observable knob-space and null confirmation without `n` placement or H1b.

**The Task-8 owner stop remains binding.** Do not run any recoverability cell without fresh explicit owner authorization; do not substitute a dynamic or adaptive OASIS frame.
