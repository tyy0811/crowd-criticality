# Magnitude probe synthesis — graded per-market discrimination RESTORED (against smooth confounds)

**Date:** 2026-06-23 · **Branch:** `s0.4-data-feasibility-spike` · **Inputs:**
`2026-06-23_magnitude_probe.md` (n=0.90, 80 seeds, extended grid), `2026-06-22_tightened_verdict.md`.
Supersedes the tightened run's "resolution-floor / split broken" reading with a **graded** restoration.

> **⚠ COLLAPSED — the finer-grid check (`2026-06-23_finegrid_check.md`) CONFIRMED this was a quantization
> artifact.** On a 0.025 grid, genuine migrations SPREAD (median 1.075, 95th pctile 1.125, max 1.125) — not
> "all at 1.05" — and the real markets' true continuous peak is **1.125, not 1.20** (the 0.15 grid had snapped
> genuine down to 1.05 and the real markets up to 1.20). The real markets sit AT the genuine 95th-pctile/max,
> inside the smooth near-critical upper tail. Pre-registered verdict: **SEPARATION COLLAPSES → resolution-floor.**
> The magnitude "restoration" below is the artifact; the live status is in the finer-grid doc.
> Two framing corrections still stand:
> (2) **"RESTORED" overstates.** At best this is **real-vs-*smooth*-genuine** discrimination, *not* "degenerate":
> a genuine near-critical process with a bursty baseline gives the same un-absorbed-structure signature, so if
> the markets are bursty-genuine they *are* near-critical and the original split (markets 1,2 not near-critical)
> was wrong. (3) **Population ledger:** only the **binary** claim — P(this migrate/not *pattern* | all
> smooth-genuine) ≈ 2%, which depends on *which* markets migrate, not how far — is grid-robust and bankable.
> The magnitude version ((0/23)² ≈ 1.5%) inherits the grid dependency and is **not** independently firm.
> Non-stationarity inflation is untouched throughout.

## Bottom line
The binary gate lost discrimination (genuine near-critical false-migrates 8–22%), but **migration MAGNITUDE
restores it**: genuine *smooth* near-critical that migrates overshoots only to **1.05** (23/23, none at
1.20, none at the 2.0 ceiling), while the real …3503/…9630 reach **1.20 — beyond the entire genuine
distribution** — and …9076 doesn't migrate (stays 0.90). So **the real …3503/…9630 are NOT behaving like a
smooth genuine near-critical market**, and the per-market reading is recovered as a *graded, measured*
statement — neither the 8-seed "earned" over-claim nor the tightened "split dead" pessimism.

## What the magnitude established (genuine side well-sampled, 23 migrations)
- genuine smooth near-critical overshoot is **bounded at 1.05** (one grid step past 1.0) — a tiny residual,
  because μ(K=12) fully absorbs a smooth ramp.
- real …3503/…9630 overshoot to **1.20** — i.e. they carry **more un-absorbed structure** than any smooth
  genuine near-critical. Pre-registered rule (result-blind): real peak > 90th pctile of G → RESTORED; both hit it.
- specificity CIs (Wilson95, 80 seeds): …3503 12/80 spec [75.6%, 91.2%]; …9630 4/80 [87.8%, 98.0%]¹;
  …9076 7/80 [83.0%, 95.7%]. The **binary** specificity straddles 90% (check 1 holds) — but the magnitude
  criterion separates cleanly where the binary cannot.

## The crucial limit this does NOT clear — and it sharpens the bursty test
Magnitude separates "**real ≠ smooth-genuine**". It does **NOT** establish "**real = degenerate**" as opposed
to "**real = genuine near-critical with a BURSTY baseline**". The 1.20 overshoot *is* "more un-absorbed
structure than a smooth ramp" — and a bursty baseline the smooth μ cannot absorb produces exactly that, even
at a genuine near-critical n. So the determining question is now **pointed and quantitative**:

> **Does a genuine near-critical process with a bursty (qr-high/swing-low) baseline overshoot to ~1.20, or
> does it too cap near 1.05?** If bursty-genuine reaches 1.20, the markets' 1.20 is explained by burstiness,
> not degeneracy, and the misspecification reading flips. If bursty-genuine still caps low, …3503/…9630's
> 1.20 is genuine excess self-excitation and the split stands.

This is the bursty-baseline chapter, now the single load-bearing test — and (per the standing note) a **new
instrument** needing its **own** matched-recovery calibration; it cannot inherit the smooth-μ specificity.
The tightened + magnitude result is the baseline it must beat.

## Honest caveats (so this favorable read stays calibrated)
1. **N=1 real observation per market.** The genuine side is well-sampled (23), but each real market migrates
   to 1.20 once. The separation is total, but it is a single realization per market.
2. **One-grid-step separation (1.05 vs 1.20).** Worth a finer n-grid near 1.0–1.3 to confirm genuine caps
   ≲1.10 and isn't a quantization artifact — cheap follow-up.
3. **Per-market bound, not <5%.** 0/23 genuine at 1.20 → one-sided 95% upper bound ≈ 12% per market; the
   *joint* "…3503 AND …9630 both at 1.20 if both genuine" is ≈1.5% — so the population claim is much firmer
   than any single market's.
4. **Smooth confounds only** — caveat from the limit above.

## Status (current best, all rounds integrated)
- **…9076 (35k):** genuine near-critical — doesn't migrate; consistent throughout.
- **…3503 / …9630:** **not smooth-genuine near-critical** (overshoot beyond all genuine) — graded, measured;
  whether that is degeneracy or burstiness is the open determinant.
- **Population:** "not all three are smooth-genuine near-critical" is robust (~1.5%), independent of any
  per-market certification; recast as an all-genuine-vs-degenerate model comparison it is the publishable core.
- **Durable deliverable:** the gate + its measured binary false-positive rate (8–22%) **and** the magnitude
  refinement that recovers graded discrimination — an honestly-characterized instrument, with the bursty
  chapter as the named determinant.

¹ …9630 cal N-mismatch (+8.8%, rate biased low); its genuine-false peaks are all 1.05 regardless, so the
magnitude conclusion is unaffected.
