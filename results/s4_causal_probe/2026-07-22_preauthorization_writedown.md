# Causal probe — pre-authorization writedown (Tasks 3–7C)

**Date:** 2026-07-22 · **Branch:** `stage2-causal-probe-freeze` · **Plan:** `docs/superpowers/plans/2026-07-22-oasis-causal-probe.md`
**Freeze commit:** `14fc14a` (Task 7B) plus the commit introducing this writedown, which completes the executable freeze; the final HEAD is recorded in the Task-8 handoff.
**Status: pre-authorization. The Task-8 owner stop is binding. No scientific, LLM, GPU, or provider-backed run has occurred or is authorized by anything below.**

## 1. What was built (Tasks 3–7B)

- **Task 3** (`6529ed2`): pure fixed-frame `CausalRefreshController` — exact categorical selection over registered pair probabilities plus the residual no-selection mass, treatment at exactly 0.5 only on selection, one immutable `StratumDraw` per stratum, per-refresh frame re-hash, symmetric parent/filler serving in the first feed slot with length preservation, fail-closed on unknown/duplicate/missing/out-of-order strata.
- **Task 4** (`d274580`): installed-OASIS integration. `apply_causal_refresh` delegates ordinary refresh construction to the production `Platform` and re-records the refresh trace so served IDs always equal the returned feed; `load_frame_eligibility_evidence` measures author/creation-round/first-readability/prior-exposure/opportunity from actual DB+trace rows; `collect_causal_outcomes` joins exactly one fail-closed outcome per assignment on native links only (no text inference); `run_oasis_minimal` gains both-or-neither `causal_frame`/`causal_controller` hooks with a byte-equivalent inert default (default exporter untouched; regression pinned).
- **Task 5A** (`3483d08`): scripted one-generation control with planted truth — fixed pre-selection potential responses, `R_plant = mean_parent(sum q)`, hidden `R_gen_frame = mean_parent(sum y)`, holdouts never reply — plus the full-platform non-LLM bridge (`run_scripted_oasis_control`) on the production wrapper/selector/estimator with the fail-closed sentinel model.
- **Task 5B** (`e4c6cb3`): disjoint recursive marker control for `chi_resp` as native quote cascades (readable r+1 horizon, equal registered support, marker-namespaced IDs, rounds offset to 2+), `CV²` pooling with equal root weight (6,144 concatenated sizes; seed-level averaging structurally impossible), and `locate_chi_peak` requiring an interior unique aggregated maximum with 12/12 seed-argmax consistency.
- **Task 6** (`b3e8f2f`): AST import firewalls (no similarity/powerlaw/Hawkes/parrot/`n_resp` in any causal module; estimator import surface pinned to records/validators/spec/math), field-by-field manifest disjointness guards with one-field-overlap power checks, `require_disjoint_seed_sets`, known violators (dropped no-selection draw, smuggled pair, denominator reconstruction, frame-hash change, duplicate native child), and the strict validator suite passing under both normal Python and `python -O`.
- **Task 7A** (`232b404`): result-blind constants frozen before generation (coverage ≥ 0.95, mean full width ≤ 0.10, power ≥ 0.80, 200k replicates, Wilson-99% half-width ≤ 0.003, seed registries pairwise disjoint); exact-selector Monte Carlo via the sufficient statistic `K = Bin(M1, 0.2) + Bin(M2, 0.4)` (the exact law of the frozen selector; power-checked in-tests against an independent per-stratum replay); banked artifact reproduces byte-identically.
- **Task 7B** (`14fc14a`): dormant recoverability runner — frozen gate clauses, canonical manifest, `--dry-run` hash preflight through root creation only, `--execute` guarded behind the Task-8 owner stop and reachable only through the scripted and marker controls (no provider/LLM import surface; AST-pinned).

## 2. Power freeze (banked, $0)

- Artifact: `results/s4_causal_probe/2026-07-22_power_calculation.json`
- SHA-256: `7e7086f8ca8bb868b6240c602848ec5c15ccd6c32681d3182d90bdf5c23596fb` (frozen in `causal_probe_spec.py`; byte-reproduced three times, including after post-freeze refactors)
- **Selected support: 8192 parents × 4 recipients (32,768 pairs; 16,384 strata).** First candidate in the frozen order to pass every cell: worst-cell mean full CI width 0.099 (plant 1.30) vs the 0.10 ceiling; coverage ≥ 0.95 in all six cells; power 1.000; zero structural failures. All 23 smaller candidates fail the width criterion (measured, recorded per cell in the artifact).
- Deterministic worst-case variance bound imported from the production estimator (never reimplemented).

## 3. Full-scale dry-run preflight (measured)

- Command: `python -m critaudit.experiments.causal_probe_recoverability --dry-run --power-artifact results/s4_causal_probe/2026-07-22_power_calculation.json`
- Dry-run manifest SHA-256: `b4d5f6a77ab491229b00e1f68c458a06438c7b19ceff346c36e3f086b41c4414`
- Frame SHA-256: `045bd40c8d36cbebe642c613de484ab439e7607a9d3de61e4235866836b63182`
- Eligibility-evidence SHA-256: `9980fbc145d5deb293ae982c2426eadbd5438e01beaf97ab70680db073b2556f`
- Wall time: ≈ 44 minutes at the full selected support (24,578 sign-ups; 16,386 reply-layout posts; canonical evidence over 32,768 pairs; 512 marker roots). Teardown before any draw, verified in the pre-draw databases: 0 refresh trace rows, 0 comments, no result artifact. `--execute` must reproduce these exact frame/evidence hashes before the first draw or fail closed.

## 4. Wall-time forecast for the Task-8 grid (measured basis — owner decision input)

The installed OASIS `Channel.read_from_send_queue` polls its response dictionary at a fixed 0.1 s sleep, so every platform action costs ~0.05–0.1 s of latency, and the concurrent sign-up phase additionally burns CPU quadratically in pending pollers. Measured at the selected support on this machine:

- sign-ups: 24,578 agents in ≈ 14 min (≈ 29/s under the concurrent gather);
- sequential creations: ≈ 10 posts/s (measured 591/min mid-run).

Per reply session forecast (sign-ups + 16,386 creations + 16,384 refreshes + up to ~2.1k scripted replies + evidence): **≈ 70–80 min**. The registered grid is 6 plants × 12 seeds = 72 reply sessions plus 72 marker sessions (≈ 3–6 min each):

- **Total forecast: ≈ 90–100 hours (≈ 4 days) of continuous wall time. $0 in API/GPU/provider cost.**

This forecast is a substrate-latency fact (the channel's polling design), not a scientific gate. Whether ~4 days of unattended wall time fits the ratified budget gate is an **owner call at Task 8**; the alternatives (patching the channel's poll interval, sessionizing differently, or treating the cost as a budget-gate failure → Branch B) all require ratification and are **not** exercised here.

## 5. Verification state

- Focused causal suite (12 files): **311 passed** (spec, records, validation, estimator, refresh incl. full-platform session, scripted control incl. bridge, marker control incl. bridge, firewalls incl. `python -O`, power, runner, pilot schedule, harness export).
- Whole-repo non-slow suite at the freeze tree: **506 passed, 2 registered skips, 44 deselected slow** (`pytest -q -m "not slow"`), `git diff --check` clean.
- Whole-branch review (Task 7C) against the ratified design: three defects found and fixed pre-commit (power-artifact path resolution off by one directory; missing cross-session evidence-hash fail-closed guard in `--execute`; cohort alignment by index rather than schedule seed under structural failures). No Critical/Important findings open.

## 6. Boundaries (unchanged)

`R_reply` is a one-generation design estimand on the fixed scripted operator; it is **not** Hawkes `n`, activates no H1b claim, and authorizes no sweep, Stage-3 work, or OASIS LLM run. The observed diagonal variance output remains `estimated_diagonal_variance_bound` with `design_only` status. Branch B remains the mechanical fail branch, verbatim:

> Bank that no recoverable OASIS regime instrument is available; retain the classical locator and OASIS accessibility findings; restrict future analysis to observable knob-space and null confirmation without `n` placement or H1b.

**The Task-8 owner stop remains binding.** Do not run any recoverability cell without fresh explicit owner authorization; do not substitute a dynamic or adaptive OASIS frame.
