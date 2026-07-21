# Dual-capture merge — FROZEN result-blind rule (recorded BEFORE the merged cohort is seen)

**Date:** 2026-06-25 · **Status:** frozen result-blind ahead of measurement. Written before the merged
over-floor cohort is computed; the rule is not adjusted after seeing which markets clear.

## Why this exists

Verification of "stop the capture" surfaced a **second, undocumented capture**: `com.crowdcriticality.brecorder`
(running since Jun 18 21:27, `~/brecorder/ws_recorder.py` → `~/b_capture.jsonl`, ~402 MB, still live) running
in parallel with the analyzed `com.crowdcrit.bcapture` (Jun 20, `~/b_capture/ws_capture.jsonl`). Two
**independent** connections to the same feed drop **different** intervals, so merging by `transaction_hash`
can fill each other's outage gaps — the one mechanism that can lift the N=3 ceiling **without new capture**,
because it attacks the exact failure that closed the salvage thread (single-connection fragmentation pushing
every new market below the clean floor).

**Standing result:** N=3 clean is confirmed **under single-capture fragmentation**. This merge can only
**lift or confirm** that ceiling, never lower it. A null merge (fills little) is the expected outcome and
N=3 stands.

## PREREQUISITE — same-feed validity GATES the merge (verify before interpreting any merged number)

The gap-fill is only valid if both processes record the **same trades**. On the overlap window (where both
were live), the **shared `transaction_hash`es must refer to identical trades**: same `asset_id`, same
`msg["timestamp"]` (server match time), same `size`. Procedure: intersect the two files' hash sets; on the
shared set, count field mismatches. **Zero mismatches → same feed → merge valid.** Any mismatches → the
streams are not the same feed (different subscription / basket / a shared-ID-different-meaning) → **merge
INVALID, abort, N=3 stands.** This is measurement-trustworthy-before-interpreting applied to the merge
itself: do not assume same-feed from "both are Polymarket recorders."

## The frozen merge rule

1. **Event set (floor count + fit):** union by `transaction_hash`, one event per unique hash. The fit-time
   is `msg["timestamp"]` — the server match time, **identical across both copies for a valid same-feed**, so
   which copy is kept does **not** move the certified timeline (the design's machine-neutrality; the n̂
   signal is server-side, not `recv_ts`).
2. **Dedup tie-break:** keep the **earlier `recv_ts`** copy. This bites only in the **degenerate case** where
   two copies of one hash disagree on `msg["timestamp"]`/`asset_id`/`size`; a **nonzero count of that case is
   a same-feed VIOLATION**, surfaced (not silently resolved). Within-file duplicate hashes likewise keep
   earliest `recv_ts`.
3. **Merged-stream gap:** a `> 60 s` interval with **no `recv_ts` from EITHER stream** — computed from the
   **un-deduped union of all `recv_ts`** from both captures (a trade received by both is doubly-confirmed
   coverage; un-deduping `recv_ts` is correct for outage detection). The 60 s is the cert's existing
   threshold — **not** a new value. "Merged up-periods" are the maximal intervals between merged gaps.
4. **Merged over-floor (necessary condition):** per market, the **largest merged fragment** = the merged
   up-period holding the most of that market's **unique** (deduped) events; the market clears iff that one
   fragment has `≥ 16000` unique events. (The same per-market-largest-fragment rule as the single-capture
   salvage screen, now on the merged stream; deterministic argmax, blind to the floor.)

## Necessary, not sufficient (carried through unchanged)

A market clearing ≥16k in the merged stream is **salvage-possible-via-merge**, not certified. Survivors owe a
**gap-guarded GoF on the merged stream's frozen fragment** (the same locked cert: eps=0.4, c=0.5, B=199,
p_flag=0.10), and may still fail for the finite-window informativeness reason already established. The merge
can put enough events on one timeline; whether that timeline supports a trustworthy n̂ is the separate GoF.

## Reading (frozen)

- **New survivor(s) (not among the clean3) clear merged ≥16k AND pass GoF → N=3 lifts, legitimately** (the
  lift came from genuinely independent dual capture, not a decision). The new cohort is real.
- **None clear / all fail GoF → N=3 stands**, brecorder is a redundant orphan.
- **Merge fills little because outages are correlated across the two independent connections → fragmentation
  is UPSTREAM** (endpoint or network, not the local process). This sharpens the parked WS-stability
  precondition for any future Stage-3 capture from "fix the connection" to "fix the endpoint/network cause";
  if outages are **un**correlated, dual-capture-and-merge is itself the recapture design.

## Implementation

`spike/s0.4/mac/dual_capture_merge.py` (bounded measurement: parse both files, same-feed check on shared
hashes, merged over-floor cohort under the frozen merged-gap rule; **no fitting** — survivors go to the
existing GoF tooling on their frozen merged fragment).
