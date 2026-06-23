# Convergent measurement — verdict (cross-review round 2 readout)

**Date:** 2026-06-22 · **Branch:** `s0.4-data-feasibility-spike` · **Driver:**
`spike/s0.4/mac/convergent_migration_cal.py` (estimator verified bit-exact vs `mu_t_hawkes.fit_mu_only`,
|Δ|=0). **Inputs frozen before the verdict:** Phase A baseline written before Phase B ran; gate decision
rule fixed in code (result-blind, finding 8).

> **⚠ SUPERSEDED — this "earned" reading is BROKEN.** Round 2 (`2026-06-22_arc_crossreview_round2.md`) flagged
> the 8-seed power + favorable +N bias; the tightened re-run (`2026-06-22_tightened_verdict.md`, 40 seeds, N
> matched down) then showed genuine near-critical false-migrates **12–22% at the markets' own fit (n=0.75)**,
> not ~0%. The 8-seed `0/8,0/8,1/8` below was small-sample luck + the +17% N-overshoot; both fixes moved
> against "earned." The split is **NOT earned** — the honest outcome is the **resolution-floor reading**
> (near-criticality not cleanly resolvable per-market at these N). Read the numbers below only as the
> superseded favorable draw; the verdict is in `2026-06-22_tightened_verdict.md`.

## Bottom line
**The per-market split is EARNED** — the cross-review blocker is refuted by measurement. Genuine
near-critical (n=0.90) under the gate, at each market's own calibrated regime with **8 seeds**,
false-migrates **0–12%**, NOT the ~50% the under-powered 18k=2/4 floor cell implied. So the real markets'
**decisive** migration is meaningful, not clean-but-unlucky:

| market | N | swing | peak@eps0.4 → peak@eps0.02 | n<1-capped | verdict | genuine p_migrate |
|---|---:|---:|---|---:|---|---:|
| …9076918150 | 34,830 | 11.7× | 0.90 → **0.90** | 0.90 | **GENUINE near-critical** | 0.00 |
| …9630680686 | 22,089 | 9.5× | 0.75 → **1.20** | 0.75 | **degenerate / mis-modelled** | 0.00 |
| …3503937838 | 18,019 | 7.7× | 0.75 → **1.20** | 0.75 | **degenerate** (12% fluke caveat) | 0.12 |

## Phase A — the frozen false-migration baseline (genuine n=0.90, off-grid shape, 8 seeds)

| regime | market (N, swing, qr) | calibrated synth (N, swing, qr) | p_migrate |
|---|---|---|---:|
| …3503 | 18019, 7.7×, 5.5 | **18563, 7.8×, 5.5** (tight) | **1/8 = 0.12** |
| …9630 | 22089, 9.5×, 8.0 | 25740, 13.3×, 6.4 (harder-swing, +N) | **0/8 = 0.00** |
| …9076 | 34830, 11.7×, 10.1 | 41218, 13.2×, 7.5 (harder-swing, +N) | **0/8 = 0.00** |

The one genuine fluke (…3503 seed 5) peaked at **1.05**, n<1-capped 0.90 — milder than any real market's
**1.20** (pinned at the n-grid ceiling, i.e. the unconstrained profile wants n>1.2, explosive). So even the
rare genuine false-migration is weaker than the real degeneracy.

## How each cross-review finding resolved
- **#1 (BLOCKER, floor non-monotone at 18k=2/4):** RESOLVED. At the tightly-matched 18k regime with 8 seeds,
  genuine false-migration is 1/8 = 0.12, not ~0.5. The 2/4 cell was 4 under-powered seeds on an
  under-non-stationary, on-grid plant. The "above floor ⇒ mis-modelled" inference is repaired: the
  discriminating quantity is the measured false-positive rate, and it is low.
- **#2 (BLOCKER, grid-extension never run on genuine synthetics):** RESOLVED. It was run here — genuine
  near-critical stays interior under extension to eps=0.02 (the migration that the bad markets show is not
  what genuine data does).
- **#3 (…3503 own-params never recovered):** RESOLVED by the pre-specified subcritical bracket — its regime
  is calibrated (the 18k row above), p_migrate=0.12.
- **#4 ("migrates to eps=0.02" mischaracterised):** SHARPENED. Under the **n<1 cap** the bad markets sit at
  an interior 0.75; only unconstrained do they jump to 1.20. Genuine near-critical does NOT prefer that
  supercritical mode. So the bad markets actively prefer an **explosive (n>1) solution** the clean model can
  only reach by going supercritical — active mis-specification, not mere non-identification.
- **#5 (calibration only at n=0.5):** RESOLVED — calibrated at the near-critical end (n=0.90).
- **#6 (ramp units + N):** RESOLVED **and extended** — the naive `ramp=swing−1` was found to *also* under-shoot
  via branching dilution + heavy-tail truncation (smoke: 7.7×→3.4×, N 18k→12k). Empirical calibration to the
  market's realized (N, qr) fixes it; realized N/swing/qr reported per regime.

## Honest caveats (keep "settled" calibrated)
1. **…3503 carries a 12% false-positive rate.** Its degeneracy is *strongly supported* (migrates decisively
   to 1.20, from 0.75, beyond the genuine fluke's 1.05) but not certain on a single realization. …9630 (0/8)
   and …9076 (genuine, 0/8) are clean.
2. **A smooth linear ramp cannot match the real markets' non-stationarity *shape*.** The calibration matched
   qr but overshot max/min swing (13× vs 9.5×/11.7×) and N (+17–18%) for the two larger regimes: the real
   markets have higher *sustained* (qr) but lower *spiky* (max/min) non-stationarity than a linear ramp
   produces. That divergence is itself a hint the real baseline is **non-linear / bursty** — the arc's
   next-chapter misspecification hypothesis, now with a quantitative tell. The 0/8 result is conservative
   (synthetics tested at *harder* swing and *more* events, still 0).
3. **N=3 markets.** The 4th over-floor market (…4676130340, ~20.5k) was below floor after the 60 s sleep-gap
   guard in this read and was not gated; apply the gate as it and others accrue.

## Verdict
Round 2 turns the arc's `SETTLED`-but-over-claimed status into **earned, with caveats**:
- **…9076 (35k): genuine near-critical, n≈0.90** — confirmed (interior under extension; genuine p_migrate=0).
- **…9630 (22k): not clean near-critical** — confirmed (migrates decisively; genuine p_migrate=0 → not a fluke).
- **…3503 (18k): not clean near-critical** — strongly supported, with an explicit 12% single-realization caveat.
- The split is **model-adequacy**, established now by a measured false-positive rate, not asserted. Caveat 2
  (non-linear non-stationarity) is the concrete handle for the next-chapter richer-model build.

Recoverability of …3503/…9630 under a bursty/non-linear-baseline model remains the open next chapter; this
run establishes they are *not clean-model near-critical*, not that they are unmeasurable.
