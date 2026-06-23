# Per-market criticality at Polymarket event counts — deliverable (LOCKED, 2026-06-23)

**Branch:** `s0.4-data-feasibility-spike`. This consolidates the four-round measurement arc into the durable
record / cross-review input. Supersedes the intermediate verdicts (`convergent_measurement`, `tightened`,
`magnitude_synthesis`) as the canonical status.

## Headline (methodological result, stated as a finding — not a negative)
**On real Polymarket trade streams, apparent near-criticality and genuine near-criticality are NOT separable
per-market at the achievable event counts (18–35k), with a smooth-μ(t) flexible-baseline Hawkes — and here is
the measured resolution floor.** A genuine near-critical (n=0.90) process at these markets' own regimes
false-migrates to a supercritical estimate **15–27%** of the time (measured, per-market N-matched), and on a
resolved n-grid the real markets' migration peak (1.125) sits **inside the genuine smooth near-critical upper
tail (own-regime 93rd–95th percentile), not beyond it.** This is the Filimonov–Sornette side of the
endo/exo dispute, settled on fresh non-HFT data with synthetic controls at every step.

## Two durable, bankable contributions
1. **Non-stationarity inflates apparent criticality.** Real markets ramp 8–12× toward resolution; a naive
   stationary Hawkes absorbs the ramp into the branching ratio, inflating n̂ toward 1 (textbook apparent
   criticality). Untouched through all four rounds.
2. **The per-market resolution floor, measured not asserted.** With a smooth-μ flexible-baseline Hawkes at
   18–35k events the gate's per-market false-migration rate is 15–27%; magnitude does not rescue it (the
   apparent 1.05-vs-1.20 separation was a grid artifact, §arc). So per-market criticality certification is not
   achievable at these counts — a quantitative floor, with the instrument and its error rate characterized.

## Per-market verdict
- **…9076 (35k):** best-supported genuine near-critical (steep profile peak at 0.90, ll(0.90)−ll(1.05)=86u,
  eps-stable, doesn't migrate) — but *consistent with* genuine, not *certified* (75% of genuine identify here).
- **…3503 (18k) / …9630 (22k):** peak at **1.125** (mild supercritical) — inside their own genuine smooth
  near-critical upper tail (93rd–95th pctile), sharp maxes (not ridges). **Not distinguishable** from genuine
  smooth near-critical that the gate mis-fit upward. The earlier "split" (these two degenerate) is **not
  supported** — they are equally consistent with genuine-near-critical-the-instrument-cannot-resolve.

## Population claim — DEMOTED to suggestive (not bankable as-is)
P(observed migrate/not pattern | all three smooth-genuine) ≈ **4%** (fine-grid rates 27.5/17.5/25%):
suggestive heterogeneity ("not all three are smooth-genuine"), but (i) it rests on the three per-market
migration rates, (ii) it is a *population* statement that says nothing about *which* market, and (iii) it
moved 2%→4% across the regrid — itself the tell it was never firm. The joint-magnitude "both at ≥1.125" (<1%)
was **not pre-registered** → kept out of the bankable column entirely; it needs its own frozen rule and a
proper all-genuine-vs-degenerate model comparison before it could be banked.

## Scope-gates on the collapse (symmetry: an under-resolved instrument can manufacture a collapse too)
- **Peak sharpness:** real argmax 1.125 is a moderately-sharp max (soft ±0.025) beating both 1.05 (−13/−27u)
  and 1.20 (−13/−18u) — not a flat ridge; steepness survived the regrid. ✓
- **Per-market N-matched:** genuine plant calibrated per regime; each real market compared to its *own*
  regime's genuine (93rd–95th pctile), not a pooled distribution across three Ns. ✓

## The four-round arc — the methodological exhibit (the part that transfers)
Every favorable reading turned out to be an **under-resolved instrument** and fell to **resolution**, never to
argument:

| round | favorable reading | the under-resolution | the resolution that broke it |
|---|---|---|---|
| 1 | "split earned" (0/8, 1/8 ≈ 0–12%) | 8 seeds (ub 31–47%) + favorable +N bias | 40 seeds, N matched down → 12–22% |
| 2 | (gate self-check) | qr-calibration overshot N +17% | swing/N-matched calibration |
| 3 | "magnitude restores it" (1.05 vs 1.20) | binary criterion conflates mild/severe | per-seed migration *magnitude* |
| 4 | "total separation, real beyond all genuine" | 0.15 n-grid (only {1.05,1.20} in 1.0–1.3) | 0.025 grid → genuine spreads to 1.125, real *is* 1.125 |

Verify-the-measurement-before-interpreting, shown working across four successive instruments on real data with
synthetic ground-truth controls at each step — the discipline the HFT endo/exo literature could not apply.

## The floor does not clear 10% anywhere in 18–100k — N-probe
The fine grid **relocated** the markets — 1.125 (mild, inside the genuine range), not 1.20 (beyond it) — so a
bursty model would be explaining un-absorbed structure that **may not exist**. The N-probe (`2026-06-23_nprobe.md`,
genuine n=0.90 at 35k/60k/100k) tested whether volume breaks the floor:

| N | genuine false-migration | Wilson 95% |
|---|---|---|
| 35k | 13% | [5.3%, 29.7%] |
| 60k | 17% | [7.3%, 33.6%] |
| 100k | 7% | [1.8%, 21.3%] |

**Read honestly (not banked as a clean result):** under-powered (30 seeds), and the frozen <10% rule used a
*point estimate* — the round-1 error one axis up — so the frozen "N-dependent" pass was declined. The
calibrated statement carries **no trend claim**: the floor **does not clear 10% anywhere in 18–100k, there is
no firm trend with N** (13/17/7, all three Wilson CIs overlap), and the data is consistent with a **roughly
flat floor in the ~7–17% band across the whole range**. So **volume does not resolve per-market certification
in the achievable range** — and a flat persistent floor is a *more robust* finding than a slowly-improving
one (it rests on no trend the seeds cannot support). The 10% threshold sits at the plausible rate, so "firm
whether <10%" is not cheaply answerable — the level, not a trend, is the honest read. (The N-probe's
non-firmness rests entirely on its own evidence — non-monotone 13/17/7, overlapping CIs, threshold at the
rate — and needs no further caveat.)

## Forward
- **The deliverable above stands** — non-stationarity inflation + the per-market resolution floor characterized
  across 18–100k + the four-round methodological exhibit. A complete, honest pre-PhD artifact.
- **Bursty chapter: not clearly motivated, held.** The markets are mild (1.125, inside the genuine range), so
  there is no large un-absorbed overshoot demanding a richer baseline; and the floor persists to 100k, so the
  question it would address is the instrument's resolution at these timescales, not the markets' structure. If
  pursued later it is a new instrument with its own matched-recovery calibration; this result is its baseline.

## Open thread (suggestive, NOT banked)
- **Does the floor depend on ramp steepness independent of N?** Observed while building the gate's `src` tests:
  genuine n=0.90 migrated ~0/16 at T=43200 s vs ~4/16 at T=32760 s, at matched nominal N≈18–20k and swing≈8×.
  This is **under-powered and confounded** — 0/16 vs 4/16 is within binomial noise at a ~12% rate (a 16-seed
  cohort cannot lock a *rate*, still less a rate *difference*), and the comparison varies T, density, and local
  ramp slope together while attributing the result to steepness. **Untested.** If it ever becomes
  decision-relevant (e.g. for transporting the floor to markets at very different timescales), measure it
  properly: many seeds, with N, density, and slope varied one at a time. Logged, not concluded.
