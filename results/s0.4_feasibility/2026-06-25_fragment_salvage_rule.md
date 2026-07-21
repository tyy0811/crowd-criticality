# Fragment-salvage screen — FROZEN result-blind rule (recorded BEFORE the screen runs)

**Date:** 2026-06-25 · **Status:** frozen result-blind ahead of any measurement; this file is written and
recorded *before* the screen sees per-market fragment counts. The rule below is fixed; it is not adjusted
after seeing which markets survive.

## Standing result this screen tests (and can only move one direction)

**The clean over-floor cohort is N=3 — that is the LOCKED standing result NOW, not pending this screen.**
The global gap-guard (`read_markets(sleep_gap_s=60)`) keeps one global longest gap-free window (~31h) and
drops 72% of events; under it only the original three markets are cleanly over the 16k floor
(`…9076918150`, `…9630680686`, `…3503937838`). This screen is a **bounded attempt to overturn N=3
UPWARD only**: it can lift the ceiling (if a dropped market has enough clean data in a single capture-up
period) or confirm it (if none do). It cannot lower it. **A null result (all candidates under floor) is the
EXPECTED outcome and changes nothing — N=3 stands.** The screen is "check whether salvage exists, expecting
it probably doesn't," not "find the salvage."

## The frozen fragment-selection rule

1. **Outage definition — unchanged from the cert's global guard.** A capture outage is a `> 60 s` gap in
   the **all-markets** `recv_ts` stream (the same 60 s the existing guard uses; **not** a new threshold).
   "Capture-up periods" are the maximal intervals between such global outages. A market being merely *quiet*
   inside an up-period does **not** fragment it — an outage is global (capture down → no market receives
   events), so only global outages cut fragments.
2. **Per-market largest clean fragment.** For each market, count its events within each global up-period;
   take the **single up-period with the most events** (deterministic argmax by event count = "largest clean
   fragment *size*"). **That one fragment only.** No searching across a market's fragments for whichever one
   clears the floor; the max-size fragment is selected blind to the floor.
3. **Necessary-condition pass.** The market's largest clean fragment has `≥ 16000` events (the floor).

This is a pure **scope change** — "one global window for all markets" → "each market's best window under the
*same* 60 s global-outage definition" — with no new threshold and no per-market gap definition.

## What a pass means — and does NOT mean (your fix, load-bearing)

The pass condition is **necessary, not sufficient.** "≥16k events in one clean fragment" answers *does enough
clean data exist in one piece* — it does **not** mean the market certifies:
- A 16k fragment that is mostly one short burst plus a long thin tail is **clean-but-uninformative**, the
  same failure the early window had; whether the fragment supports a trustworthy n̂ is decided by a real
  **gap-guarded GoF on that frozen fragment**, run afterward, not by this screen.
- This is symmetric with the cohort error just caught: raw count over-reported the *certifiable* cohort;
  fragment count could over-report the *salvageable* one. So:
  - **Screen returns zero** → option (c) is **dead**, N=3 is the real ceiling. (Cheap, decisive kill.)
  - **Screen returns nonzero** → salvage is **possible**, not pre-cleared. Each survivor goes through the
    same gap-guarded GoF as everything else, on its **frozen** largest fragment, and some may still fail.

The screen narrows what is worth the GoF compute; it does not preview the verdict.

## Scope and reporting

- **Candidates:** the markets with raw total `≥ 16000` events (only these *can* hold a ≥16k fragment). The
  three already-clean markets pass trivially (they are the global window); the **6 markets the global guard
  dropped** are the real test.
- **Reported per market (context, NOT pass criteria):** largest-fragment event count, its `recv_ts` span
  (hours), and events/hour — so a 16k fragment that is a short burst vs a spread stretch is visible going
  into the GoF decision. Only the event-count ≥16k is the screen's pass condition.

## Implementation

`spike/s0.4/mac/fragment_screen.py` (bounded measurement: one parse of the capture for per-event
`(asset_id, recv_ts)`, global up-period cut at 60 s, per-market max-size fragment; **no fitting**).
