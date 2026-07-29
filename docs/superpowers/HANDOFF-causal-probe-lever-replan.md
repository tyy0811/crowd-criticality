# HANDOFF — Causal-probe Task-8 run ABORTED on a measured blowout; record reconciled; DO NOT RERUN

**Date:** 2026-07-29 · **Branch:** `stage2-causal-probe-freeze` · **Worktree:** `/Users/zenith/Desktop/crowd-criticality/.worktrees/stage2-causal-probe-freeze` · **HEAD:** at/after `9dd7317` — the 2026-07-29 record-correction commit (DECISIONS + writedown §9) on top of the runtime-replan `cfff26b`; this handoff reconciliation is committed on top of `9dd7317` (force-added: the handoff is a git-ignored living doc). Working tree CLEAN, unpushed, unmerged.

## ⛔ STATUS — READ FIRST: Task-8 was RUN 2026-07-29 and ABORTED; DO NOT RERUN

The owner authorized the recoverability grid at `cfff26b` on 2026-07-29 (bounded five-step, ~1–1.5 h budget, `--manifest` amendment re-confirmed). It was run and **stopped on a measured budget blowout**:
- **Dry-run PASSED the hard gate** — a fresh full-scale dry-run reproduced manifest `3553d9467edef2bf5fd3bee67da5ee46d0cd93801abc1cfe47f0d9092b0f4d42` **byte-exact** (~22 min; power `b4091ab1…`, frame `045bd40c…`, evidence `9980fbc1…` all matched).
- **`--execute` ABORTED cleanly** ~24 min in, at reply cell 1 of 84. **NO result artifact was written** — `results/s4_causal_probe/2026-07-22_recoverability.json` verified absent (the writer is reached only at full completion). Worktree clean; instrument identity intact.
- **Corrected forecast: ~17–20 hours.** Each of the 72 reply cells rebuilds the full 24,578-agent platform via `env.reset()` (`run_execute` → `run_scripted_oasis_control` once per reply seed; fresh `Platform`/`AgentGraph` + 16,386 posts) at ~14.25 min/cell → 72 × 14.25 ≈ 17.1 h + 12 marker runs (5-agent, small) + predraw. ~13× the ~1–1.5 h budget.

**That prior authorization is CONSUMED. The Task-8 owner stop is binding again.** Do **NOT** run the recoverability grid / dry-run / `--execute` / any provider or scientific run without the owner's **fresh explicit** authorization (e.g. they type "authorized — run the recoverability grid"). Treat "please continue" or silence as **not** authorization — ask. Merge/push of the branch is also the owner's call.

**The ~1–1.5 h forecast and the lever-2 "retired" conclusion are SUPERSEDED.** Root cause: the "44 min" / lever-2 "~20 min" figures were action-cost extrapolations from a 303-agent A/B that omitted the dominant full-scale build term; the ~22-min full-scale dry-run should have invalidated the forecast — the integrated-measurement acceptance gate was not actually satisfied. Full corrected record (committed `9dd7317`): **DECISIONS.md `2026-07-29 CORRECTION`** and **writedown §9** (`results/s4_causal_probe/2026-07-22_preauthorization_writedown.md`).

**Durable evidence archive:** `~/crowd-crit-runs/s4_causal_probe/2026-07-29_run/` — dry-run + execute logs and the banked dry-run manifest (`3553d946…`); full SHA-256s in DECISIONS/writedown §9. The mkdtemp scratch (`predraw_verification.db`, incomplete `reply_0.6_2026072201.db`) was removed after its hashes were recorded in `9dd7317`.

## Binding constraints (unchanged)
- **Task-8 owner stop is binding.** No scientific/provider run, grid re-run, or dynamic/adaptive frame without fresh explicit owner authorization.
- **Fail-closed:** if the execute command or ANY structural gate fails → STOP; no repair, no added cell, no rerun under a changed construction.
- **Stop again before any OASIS-LLM pilot** (Task 9 is result-locking only).
- Owner prefers **prose** decisions (rejects the AskUserQuestion widget). Corrections must reach the artifact (DECISIONS.md same-day).

## What this session did — the runtime replan (all committed, runtime-only, NO re-bank)
Task 8 was authorized+launched 2026-07-23, owner-stopped ~4 h in on a forecast I wrongly stated as ~16 days (no result artifact written). The measured replan corrected TWO mis-attributions of mine and fixed the true bottleneck in the controller. Commit chain on this branch:
- `4f97b8a` **lever 3** — index the controller's O(total_pairs=32,768) per-refresh isolation scan → O(agent's pairs). Differential naive-scan proof; 210–451× isolation gate.
- `397a388` **frame-integrity amendment** — the real blocker was `_check_frame_unchanged` re-serializing+SHA-256'ing the whole frame every refresh (722 ms). Controller now decodes a PRIVATE `_operational_frame` from immutable `_frame_bytes`; `refresh` no longer re-hashes. **Posture changed detect→IMMUNE** (owner-approved) with a MANDATORY `assert_run_frame_intact()` at the run boundary. `frame` returns a fresh decode; `frame_bytes` added. (An O(1) identity fast path was REJECTED — misses nested `object.__setattr__`; regression pins it.)
- `6171480` **bridge immunity completion** — the reply bridge now reads one detached `run_frame = controller.frame` for comment routing + manifest; mid-run caller-frame mutation regression.
- `1f52136` **lever 1** — event-driven `LowLatencyChannel` (repo-local standalone, Future-only delivery, race-safe lifecycle: Future-before-enqueue; missing/dup `send_to` discarded first-wins; read-cancel pops Future so late `send_to` discarded no-leak; EXIT no Future). Wired into Task-8 causal constructors ONLY; `run_oasis_minimal` LLM path stays stock.
- `461ee19` **all-table A/B repair** — the transport A/B now enumerates all tables from `sqlite_master` (17 incl. `sqlite_sequence`), not 6 hard-coded.
- `b59326e` DECISIONS.md consolidated entry (2026-07-29). `cfff26b` writedown §8.

**Lever 2 (build-once/cold-attach): REOPENED as a DESIGN CANDIDATE — NOT approved for implementation.** [Supersedes the earlier "retired" framing, which rested on the measured-false "~20 min" figure.] The 2026-07-29 run measured the per-run full-platform rebuild as the dominant remaining cost (~14.25 min × 72 ≈ 17.1 h) — exactly what cold-attach eliminates. The spec (`docs/superpowers/specs/2026-07-28-lever2-snapshot-coldattach-design.md`) must return **through review before any code change**; this reopening authorizes design review only, not building.

## Runtime replan — what it fixed, and the total-runtime conclusion it got WRONG
The transport/runtime fixes are real and verified: per action ~100 ms → **~1 ms**; transport A/B (~303 agents) byte-identical across all 17 tables + hashes + `ProbeManifest` + ledgers + `R_reply` estimate; full-scale dry-run reproduces manifest `3553d946…`; **554 repo non-slow tests**; 96.1× timing gate; unit lifecycle 7/7.

**But the total-runtime conclusion was wrong and is SUPERSEDED.** The replan claimed **~1–1.5 hours** ("72 reply runs ~69 h → ~44 min"). That priced the per-refresh/action work but **omitted the dominant full-scale `env.reset()` rebuild term** (~14.25 min per reply run at 24,578 agents). The 2026-07-29 integrated run measured the true total at **~17–20 hours**. The levers fixed the refresh/transport cost; the per-run platform rebuild — which they do not touch — now dominates.

## Frozen instrument identity — UNCHANGED (must reproduce)
- power artifact SHA `b4091ab19cbffc90b6e508b9495fc147ad5a23e24b001148aa245054f63db660` · `results/s4_causal_probe/2026-07-22_power_calculation.json`
- dry-run manifest SHA `3553d9467edef2bf5fd3bee67da5ee46d0cd93801abc1cfe47f0d9092b0f4d42`
- frame SHA `045bd40c8d36cbebe642c613de484ab439e7607a9d3de61e4235866836b63182` · evidence SHA `9980fbc145d5deb293ae982c2426eadbd5438e01beaf97ab70680db073b2556f`
- selected support 8,192 × 4 (fixed denominator 8,192; 32,768 pairs; 16,384 strata).

## HISTORICAL / UNAUTHORIZED — the "if authorized, run" procedure (DO NOT EXECUTE)
**⚠ Retained for reference only. NOT authorized.** This is the procedure that was executed once on 2026-07-29 and aborted on the measured ~17–20 h blowout above. Its original inline time estimates ("~minutes" dry-run; "~1–1.5 h" execute) are **MEASURED-FALSE** — the real figures are ~22 min (dry-run) and ~17–20 h (execute). Do not run any of it without a **fresh explicit** owner authorization. If (and only if) a future run is separately authorized, the hard manifest-SHA gate and fail-closed rules below still apply.
1. Fresh dry-run: `env PYTHONPATH=src /Users/zenith/oasis_venv/bin/python -m critaudit.experiments.causal_probe_recoverability --dry-run --power-artifact results/s4_causal_probe/2026-07-22_power_calculation.json --work-dir <durable-workdir>` → **HARD GATE:** `shasum -a 256 <workdir>/dryrun_manifest.json` MUST equal `3553d946…`; mismatch → STOP.
2. If match, the single registered command (no other cell): `env PYTHONPATH=src /Users/zenith/oasis_venv/bin/python -m critaudit.experiments.causal_probe_recoverability --execute --power-artifact results/s4_causal_probe/2026-07-22_power_calculation.json --manifest <workdir>/dryrun_manifest.json --output results/s4_causal_probe/2026-07-22_recoverability.json` (`--manifest` = the owner-approved plan amendment; **measured ~17–20 h** — do NOT launch under a "finishes in a session" assumption).
3. Require exit 0, canonical bytes, frozen manifest/frame/power hashes, all 12 seeds, automatic gate eval with no value changed.
4. Command or any structural gate fails → STOP (no repair/added-cell/rerun).
5. Then Task 9 result-lock (plan Task 9); STOP before any OASIS-LLM pilot.

**Before any future authorized run, resolve the ~17–20 h cost first** (e.g. lever-2 cold-attach via design review, or a re-scoped run) rather than launching the current construction expecting ~1–1.5 h.

## Substrate & paths
- Python: **`/Users/zenith/oasis_venv/bin/python`** (NOT anaconda base — can't `import oasis`). Always `PYTHONPATH=src`.
- **The session Bash shell resets cwd to the MAIN repo between calls** — every command must `cd /Users/zenith/Desktop/crowd-criticality/.worktrees/stage2-causal-probe-freeze` first, or pathspecs/imports fail.
- Durable run archive: `~/crowd-crit-runs/s4_causal_probe/`.
- Plan (git-ignored): `docs/superpowers/plans/2026-07-22-oasis-causal-probe.md`. Specs (git-ignored): `docs/superpowers/specs/2026-07-28-lever{1,2,3}*.md`, `2026-07-28-frame-integrity-amendment.md`.
- Disposable benchmark scripts in the session scratchpad (`refresh_decomp.py`, `signup_scaling.py`, `controller_scaling.py`, `lever3_bench.py`, `integrated_refresh.py`, `lever1_timing.py`) — throwaway.

## Ops lessons (this session)
- Bash cwd resets to main repo between calls → always `cd` to the worktree.
- Background python prints are block-buffered → use `python -u` + `flush=True`.
- Don't run OASIS-heavy tests concurrently with a timing benchmark (contention skews it).
- Measured-not-argued: my bottom-up per-action sums were wrong TWICE (missed the frame re-hash); trust integrated at-scale measurements.

## Open
- line-189 second independent diagnostic: OPEN. H1b: blocked all branches. Merge/push: owner's call.
- **Task 8: authorized once (2026-07-29), run, ABORTED on the measured ~17–20 h blowout; authorization CONSUMED. No rerun without a fresh explicit owner authorization.**
- **Lever 2: reopened for DESIGN REVIEW ONLY (not implementation); spec must clear review before any code.**

---
**This handoff is a documentation reconciliation only. It does not authorize execution, implementation, merge, or push.**
