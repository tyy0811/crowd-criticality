# Arc cross-review — Round 2 (Claude + ChatGPT/Codex), on the convergent-measurement verdict

**Date:** 2026-06-22 · **Branch:** `s0.4-data-feasibility-spike` · **Input under review:**
`2026-06-22_convergent_measurement_verdict.md` (+ driver `spike/s0.4/mac/convergent_migration_cal.py`,
Phase A/B result files). **Process:** §7 cross-review, round 2; adversarial pass pointed at the regime-match
seam per the reviewer-of-record.

## Verdict of the round
**"Split EARNED" FAILS as stated. The weaker conclusion survives.** The convergent run weakened the round-1
blocker but did not close it: the false-positive rate is **not confidence-bounded low at 8 seeds**, the
genuine-synthetic regime is offset from the markets' on a net-unsafe direction, and the bursty-baseline
specificity — the load-bearing axis — is unmeasured. What survives: **…9076 (35k) looks genuinely
near-critical** under this gate, and **…9630/…3503 prefer a supercritical / heavier-tail mode** under the
current smooth-μ model. That directional discrimination is real and stronger than the arc had pre-review
(finding 4 sharpening). But "earned by a measured 0–12% false-migration at each market's own regime" is **not
established**.

## The decisive correction (Codex, accepted)
**8 seeds cannot bound a false-positive rate low.** Exact one-sided 95% binomial upper bounds:
**0/8 → 31.2%**, **1/8 → 47.1%**. So Phase A's "0–12%" are point estimates; the 95% upper bounds are
**31% (…9630, …9076)** and **47% (…3503)**. The round-1 blocker ("if genuine false-migrates ~50%, the real
migration is uninformative") is **pushed against but not cleared** — …3503's 47% upper bound still reaches the
danger zone. To bound below ~10% needs ≈0/30 seeds (rule of three). This was my over-claim: I stated point
estimates as if confidence-bounded.

## Regime-match seam — axis decomposition (Codex + Claude converge)
The 0/8 specificity is measured at planted **n=0.90, ~13× linear-ramp** swing; the migrating markets fit
**n=0.75, 9.5×/7.7×, bursty**. Offset on three axes — directions:

| axis | offset | direction of bias | safe? | closeable now? |
|---|---|---|---|---|
| n | 0.90 planted vs 0.75 fit | 0.90 is *harder* to tell from supercritical than 0.75 | **safe** (conservative) | yes — plant n=0.75 |
| swing / N | synth N +17%, swing 13× vs 9.5× | **N-overshoot makes identification easier → biases TOWARD "genuine doesn't migrate" → favorable → dangerous**; higher max/min swing conservative on that one axis; lower qr dangerous | **net unsafe** | yes — match N down + target swing |
| ramp **shape** | smooth-linear vs bursty | smooth μ(K=12) absorbs a smooth ramp of any magnitude; a **bursty baseline it cannot absorb leaks into n̂ → the exact false-migration used as the degeneracy evidence** | **dangerous, load-bearing** | **no — needs bursty generator** |

So of the three axes the n-offset is safe, the swing/N-offset is net-unsafe (the N-overshoot biases favorable),
and the **bursty-shape axis is the one that can flip specificity exactly where the markets sit** — and it is
unmeasured. The smooth-ramp's inability to match the markets' non-stationarity shape (qr matched, swing/N
missed) is itself the evidence the markets are bursty.

## Other accepted findings
- **"Explosive / wants n>1.2" is an overread.** The n-grid ends at 1.20; the real peak pinned there says only
  "the best *tested* grid point is the ceiling," and the n<1 cap returning 0.75 supports "a supercritical grid
  mode wins," **not** a proven explosive mode. Soften the verdict's language.
- **Calibration is loose** — 3 cal seeds, no convergence-acceptance check, targets qr not swing/N. Tighten.
- **No code bug** — the cached self-excitation path passed `--verify` bit-exact (|Δ|=0); the problem is
  claim/calibration, not the estimator.
- **(Claude add) …9076's "genuine" rests on the gate's SENSITIVITY (false-negative rate), which this run did
  not test** — it measured specificity (genuine flagged degenerate) only. The gate's false-negative rate at
  the markets' regime is unmeasured; the arc's Poisson-peaks-low control is only partial sensitivity evidence.

## What this leaves (honest, per-market — do NOT collapse)
- **…9076 (35k): genuine-near-critical — survives directionally** (interior under extension; genuine synth 0/8),
  pending the unmeasured false-negative rate.
- **…9630 (22k): prefers supercritical under smooth-μ** — directional misspecification signal; genuine 0/8
  (ub 31%); "not-clean is earned" not yet established.
- **…3503 (18k): weakest** — genuine 1/8 (ub 47%); its "not-clean" is the least certain and explicitly so.

## Path (closable now vs next chapter)
**Closable now (would actually settle axes n, swing/N, power):** re-run Phase A with **≈40 seeds** (bound the
false-positive rate), **plant n=0.75** (the markets' own fit), and a **tightened calibration** (match N down to
the real value and target swing, with a convergence-acceptance check). This either establishes a low,
confidence-bounded false-positive rate or breaks it — and the N-match removes the favorable bias.
**Next chapter (genuinely):** a **bursty/non-linear baseline generator** to measure the smooth gate's
specificity against the markets' actual baseline shape — the only axis the existing tooling cannot reach, now
a quantitatively-targeted build (qr-high/swing-low shape).

## Relabel — held
Do **not** relabel the arc to "earned-with-caveats" yet: round 2 shows "earned" is premature. The accurate
current status is **"migration discrimination survives directionally; 'not-clean' for …9630/…3503 is
suggested-not-earned pending (i) seeds, (ii) N-matched calibration, (iii) the bursty specificity probe."**
Relabel after the closable axes are run.
