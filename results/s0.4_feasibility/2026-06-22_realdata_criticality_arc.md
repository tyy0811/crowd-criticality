# Real-data criticality: is Polymarket near-critical, or is it non-stationarity? — consolidated arc

> **⚠ SUPERSEDED (2026-06-23) — the per-market split this document asserts is RETIRED.** The four-round
> measurement arc (`2026-06-22_arc_crossreview_round1.md` → `…round2.md` → `…tightened_verdict.md` →
> `2026-06-23_magnitude_synthesis.md` → `…finegrid_check.md`) showed the "1 genuine / 2 mis-modelled" split
> was an under-resolved-instrument artifact: genuine near-critical false-migrates 7–27%, and on a resolved
> grid the real markets sit at 1.125 inside the genuine tail, not beyond it. The locked finding is the
> resolution floor, not a split. **Current status:** `2026-06-23_per_market_criticality_DELIVERABLE.md`.
> Read this document as the (superseded) starting point of that arc, not its conclusion.

**Date:** 2026-06-22 · **Branch:** `s0.4-data-feasibility-spike` · **Status:** analysis core SETTLED;
one downstream question (recoverability of the mis-modelled markets) explicitly OPEN. This document
consolidates the dated writedowns (`results/s0.4_feasibility/2026-06-2*`) into one artifact — the
cross-review input and the durable record.

## Bottom line (read first)

On the first event-rich Source-B markets, the naive near-critical branching ratio (n̂ ≈ 0.77–0.88) is
**not what it looks like**, and the truth is **per-market**:

- Real markets are strongly **non-stationary** — event rate ramps **8–12× toward resolution**. A naive
  stationary Hawkes absorbs that ramp into n̂, inflating it toward criticality (textbook
  Filimonov–Sornette "apparent criticality").
- After correcting properly (flexible time-varying baseline **μ(t)** + **free kernel shape**, judged by
  the **profile likelihood** over n), exactly **one of three** markets (the highest-volume, N=35k) shows
  a **genuine, identified near-critical n ≈ 0.90** (Hardiman–Bouchaud reflexivity). The other two
  (18k, 22k) are **not adequately described by the clean Lomax + smooth-ramp model** — their apparent
  criticality is **untrustworthy under this model**.
- The split is **NOT a volume or memory floor** (both refuted synthetically — see §4): it is **per-market
  model adequacy**.
- **Open (not settled):** whether a *richer* model (leading guess: a bursty/jumpy news-driven baseline a
  smooth μ(t) cannot absorb) **recovers** a trustworthy n̂ for the two mis-modelled markets. "Untrustworthy
  under the clean model" is **not** "unmeasurable."

The durable deliverable is **the gate** (§3) — a per-market test of whether a near-critical n̂ is
trustworthy — not the three-market result.

## 1. Question & data

Does real within-2s trade dynamics show genuine crowd reflexivity (near-critical Hawkes branching ratio),
or is an apparent near-criticality an artifact of non-stationarity? This is the Filimonov–Sornette ↔
Hardiman–Bouchaud dispute — argued in HFT with a constant background and no observable exogenous driver;
here it is settled **per market on fresh non-HFT data with the resolution ramp directly in view**.

Data: Source-B forward WebSocket capture (server match timestamps, ms). Three markets cleared the event
floor (≥16k `last_trade_price`): …3503937838 (N=18k), …9630680686 (22k), …9076918150 (35k). Stream
validity confirmed: every event carries a unique on-chain `transaction_hash` (1:1, no re-emission) — the
GoF rejection is a genuine shape result, not a dirty-stream artifact ([[first-realdata-gof-shape-rejected]]).

## 2. The instrument chain (each step overturned the last — convergence by sharper measurement)

1. **Naive stationary fit:** n̂ ≈ 0.77–0.88 (near-critical-looking).
2. **Non-stationarity check:** rate ramps 8–12×; per-third n̂ rises with the rate; a stationary control
   gap ≈ 0 → the inflation is real (not an edge effect). Corroborated by the Hardiman–Bouchaud
   mean-variance estimator (independent of the MLE).
3. **Flexible μ(t):** a piecewise-constant **and** piecewise-linear baseline MLE (`mu_t_hawkes.py`,
   10/10 tests incl. synthetic ramp-recovery + analytic-gradient checks). At the *assumed* light shape,
   n̂ slides toward ~0.5 as the baseline flexes.
4. **Free shape + D-proxy (MISLEADING):** the KS statistic suggested n̂ unpinned across shape — but D is
   goodness-of-fit, not the likelihood. Superseded.
5. **Profile likelihood over n (the right object):** steep (371–1064 ll-units), with interior maxima at
   near-critical n for 2 of 3 markets → reversed toward *identified*.
6. **Known-truth calibration:** profile-over-n on synthetic regimes defines the signatures — identified =
   steep profile with interior peak at truth; non-identified = flat profile. Real markets are steep.
7. **Adversarial break-tests** (built to break, not confirm, the hypothesis-favourable reading):
   - *grid-extension (primary):* does the profile peak STAY interior, or MIGRATE to the supercritical
     boundary as the kernel grid opens to eps=0.02?
   - *matched recovery (signature):* does a synthetic at the market's own (eps, c, n, ramp, N) recover its
     planted n?
   Verdict: …9076 stays put (n=0.90, eps=0.4 interior) AND recovers → **genuine**. …3503/…9630 migrate
   (n→1.2) → **degenerate** under this model.
8. **Synthetic floor maps:** ruled out the "it's a volume/memory floor" explanation (§4).

Every estimator is TDD'd and every conclusion calibrated against known truth; the reversals are sharper
instruments correcting proxies, not instability.

## 3. The GATE (the deliverable) — a THREE-step per-market trust test

A near-critical n̂ is trustworthy only if a market passes all three:

1. **Grid-extension peak-migration** — fit free-shape + flexible μ(t); profile over n maxing over a shape
   grid opened to the heavy-tail boundary (eps→0.02). PASS = peak stays at an interior (n, eps); FAIL =
   peak migrates to the supercritical boundary (degenerate runaway).
2. **Matched recovery** — simulate at the market's own fitted (eps, c, n) + ramp + event count; PASS = the
   profile recovers the planted n with an interior peak (the interior-peak signature is trustworthy here).
3. **Synthetic-recovery-at-parameters (floor check)** — confirm the *clean* model at the market's own
   parameters recovers at its event count. This is what **distinguishes the two failure modes**:
   grid-migration + matched-recovery alone flag both *mis-modelled-but-fixable* and
   *intrinsically-non-identifiable* as "untrustworthy" without telling them apart; the floor check, by
   showing a clean synthetic at those parameters DOES recover, localises the failure to the **model, not
   the regime** → "untrustworthy because mis-modelled, try a better model" vs "untrustworthy because
   nothing can pin it."

Markets …3503/…9630 fail step 1 but PASS step 3's logic (clean synthetics recover at far lower N — §4),
so their verdict is **mis-modelled, recoverability open** — not intrinsically unmeasurable.

## 4. Why it is NOT a floor (both floor stories refuted synthetically)

The split correlated with volume (identified = 35k; degenerate = 18k/22k), suggesting an identifiability
floor. Two synthetic maps refuted it:

- **floor_map (N × ramp, at eps=0.4):** a planted near-critical n=0.85 recovers at every cell — N down to
  ~10k, ramp up to 16×. Floor <10k; (N, ramp) do not gate it.
- **floor_eps_map (N × kernel memory, at ramp=10×):** heavier tails floor LOWER, not higher (eps=0.1
  recovers at N≈3.5k; eps=0.2 at ≈5.8k). Floor <~12k everywhere on the clean surface.

**Modus tollens:** clean models at these parameters recover well below their event count, across the whole
ramp and tail range; markets 1,2 sit *above* that yet do not recover; therefore markets 1,2 are **not
clean models**. This is what licenses §3's "mis-modelled" — and *only* that. It does **not** establish
"not genuine" or "not recoverable."

**Debiased re-run (code-review hardened, 2026-06-22, `floor_map_corrected.py`).** A code review found
the original floor maps carried three biases toward the misspecification reading: the recovery criterion
counted *undershoots* (peak below plant) as identified; the test grid *contained* the planted shape
(home-field bonus a real market — whose true shape sits between grid nodes — never gets); and one fixed
seed per cell. Re-run with the truth planted **off-grid** (eps=0.35, c=1.7 between nodes), recovery =
**peak within ±0.10 of the plant** (excludes undershoot *and* runaway), and **MC replication**: floor is
**still <12k** (10k 3/4, 14k 4/4, 24k/32k 4/4 seeds). The modus tollens above holds on the corrected,
principled measurement — not the lucky hedge it originally rested on.

## 5. Implications (both directions)

- **Recoverability (upside, open):** misspecification — unlike intrinsic non-identifiability — is in
  principle fixable. A model that captures what markets 1,2 actually do (leading guess: a jumpy,
  news-/regime-driven baseline a smooth μ(t) cannot absorb) might recover an identified n̂. So markets 1,2
  are **not necessarily out of the subject pool**; the gap is directly testable (the next chapter).
- **Cross-model comparison (complication):** if different markets need different models, n̂ is the spectral
  radius of *whichever kernel you fit*, so comparing n̂ across model types for the eventual "criticality
  predicts skill" test is not obviously valid. A **model-heterogeneous subject pool** is a real
  complication, named here while the reason is fresh.

## 6. Open thread / next chapter

**What exactly is the misspecification in markets 1,2?** A real new-model build, not a quick check: test a
**bursty/jumpy baseline** (jumps / regime shifts vs the smooth ramp) and/or a **non-power-law kernel**
against their data, and re-run the three-step gate. Cross-review should help scope the baseline form
before committing. Until then, markets 1,2's near-criticality stays **untrustworthy-pending-richer-model**.

## 7. Caveats

- **N = 3 markets.** The per-market split (1 genuine, 2 mis-modelled) is small-sample; the capture stream
  is ongoing validation (apply the gate to new event-rich markets as they accrue).
- **Per-market verdicts carry single-realization noise.** MC replication of the corrected floor map shows
  genuine near-critical data false-migrates on a single fixed grid ~once in four near the boundary (an 18k
  cell came back 2/4). The real split is more robust than that — markets 1,2 migrated *decisively and
  monotonically under grid extension*, not one coin-flip — but a single market's verdict is noisy, so the
  gate is best applied with replication / the grid-extension trajectory, not a single fixed-grid peak.
- The gate is validated against synthetic ground truth at each step (incl. an independent confirmation
  that the migration step discriminates: pure-Poisson peaks low, near-critical stays interior); it has not
  yet been run on a large real cohort.
- All n̂ are model-conditional (§5, cross-model point).

## 8. Tooling

`spike/s0.4/mu_t_hawkes.py` (μ(t) estimators: constant + linear bases, `fit_mu_only` for the profile;
10/10 tests). Drivers + dated writedowns: `spike/s0.4/mac/{nonstationarity_check, hb_meanvar_check,
mu_t_sweep, mu_t_sweep_smooth, joint_fit_grid, profile_ll_ridge, synth_joint_recovery,
synth_profile_calibration, matched_recovery, grid_extension_peak, floor_map, floor_eps_map}.py` and
`results/s0.4_feasibility/2026-06-2*`. Memory: [[nonstationarity-inflates-nhat]],
[[first-realdata-gof-shape-rejected]], [[gof-power-floor-16k]].
