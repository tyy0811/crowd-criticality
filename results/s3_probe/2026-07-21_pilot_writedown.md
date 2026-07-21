# Sub-increment 3 — OASIS accessibility pilot writedown

**Date:** 2026-07-21 · **Branch:** `stage2-probe-pilot` (off `main` @ `b54a131`) ·
**Authorization:** owner 2026-07-21, **locator-PASS-alone** ("the pilot measures channel
accessibility, so the failed n_resp transform is not relevant to authorization"). Constraints
enforced verbatim: frozen exposure gate; ALL response values DESCRIPTIVE — no OASIS-transfer,
regime, H1b, or line-189 independence claim in any branch.

## Result: **ACCESSIBLE** (frozen gate cleared with margin)

- **5/5 markers exposed** (floor: ≥4) · **66 total marker exposures** (floor: ≥10, 6.6×) ·
  export fail-closed clean (804 events).
- Per-marker (descriptive only): round 2 → 22 exposures, tree 2, resp/exp 0.045 · round 4 → 23,
  tree 5, 0.174 · round 6 → 11, tree 1, 0.0 · round 8 → 4, tree 1, 0.0 · round 10 → 6, tree 1,
  0.0. The early-injection design carried the gate (rounds 2/4 dominate); the pool-dilution decay
  across later injections is visible and consistent with the banked windowB2 fact (a single
  round-15 injection drew 0 exposures). One marker seeded a 5-event true-link tree.
- Caveats inherited and restated: finite-memory-horizon; exposure-volume. Nothing here
  calibrates χ_resp on OASIS, certifies transfer, or touches H1b/line-189.

## Run record

- **Window 1 (10:40–10:46Z, ≈$0.10): ABORTED by the loud-400 guard at smoke round 1** — the
  runner passed a bare host where the registered form is the `/v1`-suffixed base URL; every chat
  call 404'd; the guard failed the window in 3 minutes with zero science lost. Fix: fail-fast
  `/v1` assertion in the runner + the pre-launch probe now exercises chat-completions itself.
- **Window 2 (10:47:42Z → 13:09:28Z ≈ 142 min ≈ $2.60): smoke PASS** (22 s; explicit-schedule
  marker posted; 18 calls exactly; 0 rejections) → **pilot proper 135.3 min**, 1,000 calls,
  5,996,397 tokens, **0 rejections** (loud-400 guard silent end-to-end) → DB copied durable
  before any read → frozen gate evaluated → teardown verified (`modal app list` → 0 running).
- Pilot total ≈ **$2.70 upper bound** (dashboard authoritative); project cumulative ≈ $13.7 of
  $60. Raw artifacts durable at `~/crowd-crit-runs/s3_probe_pilot/` (trace DB, usage, logs,
  runner, status).

## Standing

Sub-increment 3 is COMPLETE: χ_resp certified as a ground-truth critical-point locator (merged,
PR #10); n_resp unactivated with the collision+censor gap measured; §9a/§9b retired; Option B
unfired and frozen for future use; **and the injection channel is demonstrated ACCESSIBLE on the
OASIS substrate** — the precondition any future OASIS-side χ_resp calibration needed. OPEN:
line-189 independent second diagnostic; H1b (blocked in all branches); OASIS-side χ_resp/n_resp
calibration (a future increment's spec-first question, NOT begun here).
