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

## 0b. Owner review round 2 (2026-07-23) — two critical and four important findings, all repaired

Commits `b6a8675`, `5607191`, `1a40755` (test-first; every owner reproduction now raises):

1. **F2 was incomplete (critical):** the gate hash-checked evidence bytes without deserializing or provenance-validating them, and ignored run manifests. It now deserializes `FrameEligibilityEvidence` from canonical bytes (`frame_eligibility_evidence_from_bytes`, byte-round-trip enforced), runs `validate_frame_provenance`, and verifies every run's `ProbeManifest`: stream label, raw seed against the registered per-cell derivation (position by position — reordering raises), frame/root/pair registries, ledger-consistent assignment IDs, outcome children within the event registry, and grid-wide run-ID uniqueness. The owner's hash-consistent-invalid-evidence and reordered-manifest reproductions are locked as tests.
2. **F4 modeled the wrong cross-cell law (critical):** execution had reused each raw registered seed across all six plants, nesting the potential schedules (shared uniforms) and replaying identical selection/treatment streams across cells, while the banked simulator draws cells independently. Execution now derives each (registered seed, cell) child seed via the registered `derive_cell_seed` (`RECOVERABILITY_CELL_STREAM = 941`), making cells independent — the law the banked simulator describes. The simulator is unchanged; the banked artifact byte-reproduced after the repair, so the frozen SHA stands, and the gate verifies the derivation in every run manifest.
3. **Remaining serving-isolation cases (important):** NaN treatment uniforms raised nowhere and silently became holdouts → validated like selection draws; unselected same-round co-stratum parents could ride into the served feed organically → stripped (the selector alone decides serving); a future-round registered parent in a stratum-path background → raises; feed shrinkage → raises at serve time; `parent_seen_in_background` now means a served-feed breach, with benign deduplicated raw-background occurrences recorded as the separate `parent_in_raw_background` diagnostic instead of being mislabeled leakage.
4. **Omitted eligibility finding (important):** complete same-action opportunity is now MEASURED conservatively as recipient-signed-up AND parent-is-root-post — the case for which all three registered same-actions (comment on the post; `quote_post`/`repost` of a `common`/root post, which record `original_post_id = parent`) land natively on the parent. For a derived parent at least one native same-action is lost, but the exact resolution is action- and type-specific (e.g. `quote_post` of a quote/repost and `repost` of a repost resolve to root, whereas `repost` of a quote keeps the quote as parent), so the predicate requires a root parent as the conservative sufficient condition rather than claiming a blanket redirect. A derived parent fails provenance. *(Round-3 minor follow-up 2026-07-23: docstring wording corrected to match this precise OASIS behavior — `repost` of a quote does not redirect to root.)*
5. **Plan amendment (important):** the plan's registered Task-8 command was amended to carry `--manifest <banked dry-run manifest>` as a dated prospective amendment, before any authorization or execution. See §3's provenance caveat and §7 — the plan is git-ignored, so the freeze commit does not track it; the writedown carries the amended command text.
6. **Wording (important):** the dry-run report and this record claim precisely that provider INFERENCE is uninvoked and fail-closed (the sentinel wrapper is constructed but raises on any model call); "unreachable" is retired.

## 0c. Owner review round 3 (2026-07-23) — one critical, one important, two minor, all repaired

Commits `012bd44` (no-selection isolation), `b29ee6e` (gate disjointness + wording) (test-first; every owner reproduction now raises):

1. **F2 still incomplete in the pure gate (critical):** `evaluate_recoverability_gate` validated reply and marker evidence separately but never applied `require_disjoint_manifests` — that firewall ran only in the execution driver, so a marker manifest forged to share a reply run ID PASSED the advertised pure gate. The gate now collects every reply run manifest and every marker manifest and applies the full reply×marker disjointness firewall itself. An evaluator-level regression covers every forge-able manifest field (run_id, frame_id, round_ids, event_ids, pair_ids, assignment_ids each raise); `seed_stream_id` and `raw_seed` are proven structurally non-colliding because the per-cohort manifest validators pin them to disjoint stream labels and seed registries.
2. **Serving isolation failed open on no-selection (important):** `refresh()` returned the raw background before any isolation check on the residual no-selection mass. It now runs `_assert_no_selection_isolation` before the early return — a same-round candidate parent or a future-round undrawn parent appearing organically in a no-selection draw's background raises; both cases are test-locked (a clean no-selection background is still returned verbatim).
3. **Writedown plan-amendment contradiction (minor):** §0b and §3 now agree, with the git-ignored-plan provenance caveat made explicit and the amended command text carried in §7.
4. **Overclaimed wording (minor):** the runner module docstring no longer says "no provider path is reachable" (it says inference is uninvoked and fail-closed and no provider client is imported); the eligibility-evidence docstring states the root-parent requirement as the conservative sufficient condition rather than a blanket redirect claim.

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
- The frame and evidence hashes reproduced **byte-identically across four independent full-scale dry-runs** (2026-07-22 pre-repair; 2026-07-23 after each of the first, second, and third repair rounds — the round-3 run confirms the gate/isolation changes did not perturb the pre-draw path). The manifest hash `3553d946…` is stable across all three post-re-bank runs; durable copies of the banked manifests sit in `~/crowd-crit-runs/s4_causal_probe/`.
- Wall time: ≈ 44 minutes per full-scale dry-run at the selected support (24,578 sign-ups; 16,386 reply-layout posts; canonical evidence over 32,768 pairs; 512 marker roots). Teardown before any draw, verified in the pre-draw databases every time: 0 refresh trace rows, 0 comments, no result artifact.
- **Execute-side enforcement (review F1):** `--execute` now REQUIRES `--manifest <banked dry-run manifest>`; it checks the frozen frame hash against the manifest up front, recreates the banked evidence hash in a dedicated pre-draw verification session before any draw anywhere, and enforces the same evidence hash pre-draw inside every live session. The plan's registered Task-8 command was amended (dated, prospective) to append `--manifest`. **Provenance caveat:** the plan is a living, git-ignored document per repo convention, so freeze commit `61d642b`/this branch does NOT track the amendment; the exact amended command text is reproduced in §7 of this committed writedown so the freeze artifact captures it. The amendment must be re-confirmed by the owner before authorization.

## 4. Wall-time forecast for the Task-8 grid (measured basis — owner decision input)

The installed OASIS `Channel.read_from_send_queue` polls its response dictionary at a fixed 0.1 s sleep, so every platform action costs ~0.05–0.1 s of latency, and the concurrent sign-up phase additionally burns CPU quadratically in pending pollers. Measured at the selected support on this machine:

- sign-ups: 24,578 agents in ≈ 14 min (≈ 29/s under the concurrent gather);
- sequential creations: ≈ 10 posts/s (measured 591/min mid-run).

Per reply session forecast (sign-ups + 16,386 creations + 16,384 refreshes + up to ~2.1k scripted replies + evidence): **≈ 70–80 min**. The registered grid is 6 plants × 12 seeds = 72 reply sessions plus 72 marker sessions (≈ 3–6 min each):

- **Total forecast: ≈ 90–100 hours (≈ 4 days) of continuous wall time. $0 in API/GPU/provider cost.**

This forecast is a substrate-latency fact (the channel's polling design), not a scientific gate. Whether ~4 days of unattended wall time fits the ratified budget gate is an **owner call at Task 8**; the alternatives (patching the channel's poll interval, sessionizing differently, or treating the cost as a budget-gate failure → Branch B) all require ratification and are **not** exercised here.

## 5. Verification state (post round-3 repair)

- Whole-repo non-slow suite at the round-3-repaired tree: **535 passed, 2 registered skips, 44 deselected slow** (`pytest -q -m "not slow"`), `git diff --check` clean.
- Test-locked owner reproductions now include: the pure gate rejecting a cross-cohort forged marker manifest on every forge-able field and the structural non-collision of the seed registries; no-selection isolation raising on both same-round and future-round organic parent leaks (clean background still returned verbatim); the gate deserializing and provenance-validating evidence (hash-consistent-invalid and wrong-author both raise); reordered seed manifests raising on the registered per-cell seed derivation; the bridge failing closed before the first draw on a wrong banked-evidence hash; canonical frame/manifest/evidence byte round-trips; and the brute-force cross-check of the aligned power law.
- Power module unchanged since the round-2 re-bank; the on-disk artifact SHA is `b4091ab1…` and the round-2 banked dry-run manifest still loads canonically under the round-3 code with SHA `3553d946…`. The dry-run generating path is untouched in round 3; a fresh full-scale dry-run at the round-3 tree reproduced the banked frame/evidence/manifest hashes (§3).
- Review history: Task-7C whole-branch review fixed three defects pre-commit; owner review round 1 (six findings), round 2 (two critical, four important), and round 3 (one critical, one important, two minor) — all repaired and test-locked.

## 6. Boundaries (unchanged)

`R_reply` is a one-generation design estimand on the fixed scripted operator; it is **not** Hawkes `n`, activates no H1b claim, and authorizes no sweep, Stage-3 work, or OASIS LLM run. The observed diagonal variance output remains `estimated_diagonal_variance_bound` with `design_only` status. Branch B remains the mechanical fail branch, verbatim:

> Bank that no recoverable OASIS regime instrument is available; retain the classical locator and OASIS accessibility findings; restrict future analysis to observable knob-space and null confirmation without `n` placement or H1b.

**The Task-8 owner stop remains binding.** Do not run any recoverability cell without fresh explicit owner authorization; do not substitute a dynamic or adaptive OASIS frame.

## 7. Amended Task-8 command (committed record of the git-ignored plan edit)

The plan's registered Task-8 execute command was amended (dated 2026-07-23, prospective) to require the banked dry-run manifest. Because the plan is a living, git-ignored document, this writedown carries the amended text so the freeze artifact captures it. The dry run writes `dryrun_manifest.json` in its work directory; that file is the required `--manifest` input, and its SHA-256 must equal the handoff manifest hash `3553d946…`:

```bash
env PYTHONPATH=src /Users/zenith/oasis_venv/bin/python -m critaudit.experiments.causal_probe_recoverability \
  --execute \
  --power-artifact results/s4_causal_probe/2026-07-22_power_calculation.json \
  --manifest <work-dir>/dryrun_manifest.json \
  --output results/s4_causal_probe/2026-07-22_recoverability.json
```

The runner refuses `--execute` without `--manifest`, checks the frozen frame hash against the manifest up front, recreates the banked eligibility-evidence hash in a dedicated pre-draw verification session before any draw, and enforces the same evidence hash pre-draw inside every live session. This amendment is a safety direction only; it authorizes nothing.
