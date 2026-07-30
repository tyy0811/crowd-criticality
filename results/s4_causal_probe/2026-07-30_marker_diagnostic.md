# Task-0 marker measurement — owner-authorized bounded diagnostic (2026-07-30)

**Status: MEASUREMENT COMPLETE — NO CANDIDATE PASSED. Implementation remains halted.**
Companion machine-readable record: `task-0-marker-measurement.json` (same directory).
Total wall: **~7 minutes** of the 2-hour ceiling (crosscheck 55 s real + sweep 15 s simulated).

## Protocol compliance

| Item | Requirement | Compliance |
|---|---|---|
| 1 | Preserve 4 untracked Task-0 files; no commits/plan edits | Unchanged; `git status` identical before/after; nothing committed |
| 2 | Real 6-plant grid, 12 marker seeds, unanimity rule, artifact boundary fixed | All untouched; no seed-count sweep; validators/locator code unmodified |
| 3 | Temporary CPU simulator in /private/tmp; results through REAL `aggregate_marker_cell` + `locate_chi_peak` | `scratchpad/marker_measure/marker_sim.py`; every verdict from the real, unmodified functions |
| 4 | Cross-check vs real OASIS at 32×4, 6 plants × 12 current seeds, exact tree-size equality | **72/72 exact** — tree sizes, χ_resp, AND full manifests byte-equal |
| 5 | Predeclared ladder (4:{64,128,256,512}; 6:{32..512}; 8:{32..512}) | All 14 supports × 3 panels evaluated (complete matrix) |
| 6 | Three predeclared disjoint 12-seed panels + holdout | A=717201–12, B=727201–12, C=737201–12, holdout=747201–12 (disjoint from every registered/fixture/shadow registry). **No candidate passed → no selection → holdout not applicable** |
| 7 | Real-path confirm of selected support | Not run — nothing selected (protocol: applies only to a selected candidate) |
| 8 | 2 h ceiling; failure stops measurement, no adaptive retries | Stopped at the null result; no added candidates; ~7 min used |
| 9 | Write only the two report files | This file + the JSON, both in git-ignored `.superpowers/sdd/` |

Registry note (disclosed): `_validate_marker_manifest`/`locate_chi_peak` read `MARKER_SEEDS`/`MARKER_ROOT_COUNT`/`MARKER_ROUNDS` from REC-M module globals, so each evaluation re-points those three globals to the panel/candidate under `try/finally` — the same mechanism the signed-off Task-0 conftest uses. The validator/locator **code** ran unmodified; grid, panel size 12, unanimity, and boundary rules untouched.

## Exact-equivalence check (simulator validation)

Real `run_recursive_marker_control` vs simulator at 32×4 for all six plants × seeds 515201–515212: **all 72 runs exactly equal** in per-run tree-size tuples, χ_resp, and complete `MarkerManifest` contents (55.2 s real, 0.05 s simulated). The simulator replicates the driver's RNG (`default_rng(SeedSequence(seed, spawn_key=(912, 921)))`, one `float(rng.random())` per (parent, slot) in traversal order), sequential post-id assignment, star-shaped root attribution, and root-id-ordered size extraction. Transfer to other supports is structural: the driver loop has no support-dependent branches (read-verified); roots/rounds only change iteration counts of identical logic.

## Pass matrix (verdicts from the real, unmodified `locate_chi_peak`)

Consistency = per-seed argmax agreement with the pooled argmax, out of 12 (rule requires 12/12).

| rounds×roots | Panel A | Panel B | Panel C |
|---|---|---|---|
| 4×64  | FAIL 2/12 (argmax 2) | FAIL 2/12 (argmax 1) | FAIL 3/12 (argmax 3) |
| 4×128 | FAIL 4/12 (argmax 1) | FAIL 5/12 (argmax 1) | FAIL 3/12 (argmax 1) |
| 4×256 | FAIL 5/12 (argmax 1) | FAIL 4/12 (argmax 1) | FAIL **boundary argmax 0** |
| 4×512 | FAIL 6/12 (argmax 2) | FAIL 7/12 (argmax 1) | FAIL 4/12 (argmax 1) |
| 6×32  | FAIL 1/12 (argmax 1) | FAIL 5/12 (argmax 2) | FAIL 5/12 (argmax 2) |
| 6×64  | FAIL 4/12 (argmax 2) | FAIL 4/12 (argmax 1) | FAIL 5/12 (argmax 3) |
| 6×128 | FAIL 6/12 (argmax 1) | FAIL 4/12 (argmax 2) | FAIL 4/12 (argmax 2) |
| 6×256 | FAIL 5/12 (argmax 1) | FAIL 5/12 (argmax 1) | FAIL 5/12 (argmax 1) |
| 6×512 | FAIL 6/12 (argmax 2) | FAIL 4/12 (argmax 1) | FAIL 6/12 (argmax 1) |
| 8×32  | FAIL 4/12 (argmax 1) | FAIL 6/12 (argmax 2) | FAIL 3/12 (argmax 2) |
| 8×64  | FAIL 3/12 (argmax 2) | FAIL 5/12 (argmax 1) | FAIL 5/12 (argmax 3) |
| 8×128 | FAIL 7/12 (argmax 1) | FAIL 4/12 (argmax 2) | FAIL 2/12 (argmax 2) |
| 8×256 | FAIL 3/12 (argmax 1) | FAIL 6/12 (argmax 1) | FAIL 5/12 (argmax 1) |
| **8×512 (registered)** | **FAIL 5/12 (argmax 2)** | **FAIL 3/12 (argmax 1)** | **FAIL 2/12 (argmax 3)** |

Best consistency observed anywhere: **7/12** (4×512 B; 8×128 A). 42/42 evaluations failed. Selection: **none**. Holdout: not applicable.

## The load-bearing finding: the failure is structural, not small-sample

At the **registered production support 8×512** (aggregated over 12 seeds = 6,144 trees/cell):

- Aggregated χ_resp across the grid (panel A): `[1.081, 1.637, 1.697, 1.632, 1.587, 1.280]` — the four interior cells (0.92–1.08) lie within **~7%** of each other; the top three within ~4%. Panels B and C are equally flat.
- Per-seed argmax positions over all 36 panel seeds: cell 1 (0.92) ×13, cell 2 (0.97) ×13, cell 3 (1.03) ×7, cell 4 (1.08) ×3 — per-seed argmaxes scatter over **all four** interior cells.
- The pooled argmax itself moves across panels (2 → 1 → 3): even 6,144 pooled trees cannot resolve which near-critical cell is the peak.
- Unanimity (all 12 seeds at one cell) at this dispersion has probability of order `0.4^12 ≈ 2e-5`. Consistency counts do not trend toward 12 with support: growing roots 64→512 moved the best panel from 2/12 to at most 7/12.

**Consequence beyond Task 0:** this corrects my earlier premise, as the owner anticipated — production 8×512 had never empirically cleared this check (dry-runs stop before marker cascades; the aborted executes died in the first reply cell). On this evidence the registered instrument itself would fail-closed at `locate_chi_peak` if a Task-8 grid ever reached the marker-aggregation stage: the registered `MARKER_SEEDS` are one specific draw, and its probability of satisfying unanimity at 8×512 is of order 1e-5–1e-4. The Task-0 fixture question ("which small support passes?") is **mooted** — no support in the ladder passes, including production.

## Caveats

- **Selected-on-outcome (predeclared):** any ladder selection would have been chosen *because* it passes the locator — tolerable only as test-fixture infrastructure with the basis recorded. As executed, nothing was selected, so no selection bias enters any artifact.
- The registered seed draw itself was never swept (protocol keeps the registered registry out); the ~1e-5 figure is an order-of-magnitude reading of the measured dispersion, not a computed exact probability.
- The 4-rounds arm produced one boundary-argmax failure (4×256 C, pooled peak at 0.60) — the truncated-depth χ surface is qualitatively different at rounds=4; reported, not interpreted.
- Simulator equality is proven exhaustively at 32×4; other supports rest on the structural-transfer argument above.

## State after measurement

Worktree byte-identical to pre-measurement: the four untracked Task-0 files unchanged, no commits, no plan/spec edits, `src/` untouched. Scratchpad holds the simulator, scripts, and raw `crosscheck.json`/`sweep.json`. Rev 6, Task-0 restart, commits, and Tasks 1–9 all remain unauthorized pending owner review of this report.
