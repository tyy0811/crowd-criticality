# Tightened re-run — verdict: "split earned" is BROKEN; resolution-floor reading stands

**Date:** 2026-06-22 · **Branch:** `s0.4-data-feasibility-spike` · **Driver:**
`spike/s0.4/mac/convergent_migration_cal.py --tight` (estimator verified bit-exact). **Supersedes** the
"split earned" reading of `2026-06-22_convergent_measurement_verdict.md`.

## Bottom line
The corrected measurement **reverses** the favorable reading. With **40 seeds** and **N matched down** (the
+17% favorable bias removed), genuine near-critical at the markets' own fit (**n=0.75**) false-migrates
**12.5–22.5%** — not the ~0% the 8-seed run implied. So the real markets …3503/…9630 migrating is a
**~1-in-5 event under "genuine"** and is **not clean evidence of degeneracy**. The per-market split is
**NOT earned**. This is the **resolution-floor outcome**: near-criticality is **not cleanly resolvable
per-market** at 18–35k with this smooth-μ gate — a real Filimonov–Sornette result (apparent criticality is
genuinely hard to rule out at these N), now established by measurement.

## The numbers (genuine false-migration, 40 seeds)
| plant n | …3503 (18k) | …9630 (22k) | …9076 (35k) |
|---|---|---|---|
| **0.75 (markets' own fit)** | **8/40 = 20.0%** (ub 33%) | **5/40 = 12.5%** (ub 25%) | **9/40 = 22.5%** (ub 36%) |
| 0.90 (conservative) | 8/40 = 20.0% (ub 33%) | 3/40 = 7.5% (ub 18%)¹ | 4/40 = 10.0% (ub 21%) |

¹ N-mismatch (realized 24,029 vs 22,089, +8.8% → biased low). All n=0.75 cells N-matched (verify lines in
`2026-06-22_phaseA_tight.md`). Calibration qr undershoots market qr in every cell (4.5–7.2 vs 5.5–10.1) —
the bursty signature: the markets are *more sustained-non-stationary* than any smooth ramp.

## Why the 8-seed reading was wrong (both errors pointed the favorable way)
- **Power:** 0/8 has a 31% binomial upper bound; a true 12–22% rate produces 0/8 routinely. The 8-seed run
  under-sampled it (…3503's 1/8 was the only one that surfaced — its true rate is ~20%).
- **Favorable N-bias:** the qr-calibration overshot N by +17%; more events → easier identification → genuine
  migrates *less*. Matching N down moved every cell up. Both fixes pushed the same way — against "earned."
- **n-axis direction was backwards.** Round 2 (Codex+Claude) reasoned n=0.90 is "harder to tell from
  supercritical," so 0.90 conservative / 0.75 safe. **Empirically the opposite:** n=0.75 migrates *more*
  (12.5–22.5%) than 0.90 (7.5–20%). The markets' own n=0.75 is the **higher** false-positive regime, not the
  safe one. So planting 0.90 in the convergent run made it look cleaner than the markets' actual regime.

## What this means
- **Per-market certification is unreliable at these N.** The gate's specificity at the markets' own fit is
  **78–88%** (false-positive 12–22%), below the >90% a confident per-market verdict needs. A single market's
  migration is weak evidence.
- **The bursty axis can only make it worse.** A bursty baseline the smooth μ(K=12) cannot absorb leaks into n̂
  and manufactures migration → genuine false-migration would be *higher* than the smooth 12–22% measured here.
  The markets' qr-undershoot confirms they are bursty. So the conclusion is robust to, and only reinforced by,
  the open axis — it cannot rescue "earned."

## Residual threads (open, NOT claims — could partially rescue *some* discrimination)
1. **Migration magnitude, uncaptured here.** The binary gate records migrated/not, not how far. In the 8-seed
   run the one genuine fluke stopped at **1.05** while the real markets reach **1.20** (n-grid ceiling). If
   genuine false-migrations cluster at 1.05 and real markets at 1.20, *magnitude* could still discriminate
   where the binary does not. This run did not log per-seed peaks — a cheap follow-up.
2. **Joint pattern (secondary).** P(observed pattern | all 3 genuine) ≈ 0.20·0.125·(1−0.225) ≈ **2%**, so
   "all 3 are clean near-critical" is unlikely — there is *population-level* heterogeneity. But this needs a
   degenerate-alternative model to become a per-market likelihood ratio, and it does not license *which*
   market is which.

## What survives
- **Non-stationarity inflates naive n̂** (8–12× ramp) — untouched, solid.
- **The gate is now an honestly-characterized instrument** — its per-market false-positive rate is measured
  (12–22% at these N, against smooth confounds; worse under burstiness). That characterization is the durable
  methodological contribution.
- The durable deliverable shifts from "a per-market split (1 genuine / 2 degenerate)" to **"near-criticality
  is not cleanly resolvable per-market at the achievable event counts; here is the gate and its measured
  false-positive rate"** — the Filimonov–Sornette reading, established not asserted.

## Verdict / relabel
Split **NOT earned** (nor cleanly "settled" either way per-market). Honest status: **the smooth-μ 3-step gate
cannot confidently certify per-market near-criticality at 18–35k; genuine false-positive 12–22% (markets' own
n), worse under the markets' established burstiness.** …9076 not migrating is *weakly* consistent with genuine
but is not a confident certification. Relabel the arc away from any per-market split, to the resolution-floor
reading, with the migration-magnitude probe and the bursty-baseline model as the two routes that could
(partially) restore discrimination.
