# Arc cross-review — Round 1 (Claude + ChatGPT/Codex)

**Date:** 2026-06-22 · **Branch:** `s0.4-data-feasibility-spike` · **Input:**
`results/s0.4_feasibility/2026-06-22_realdata_criticality_arc.md` · **Process:** project norm §7
(Claude/ChatGPT cross-review). Reviewer-of-record (human) accept/reject recorded in §Decision.

## Verdict of the round
The arc's **`SETTLED`** framing is **over-claimed**. The per-market split (1 genuine / 2 mis-modelled)
is **not established** — but **not refuted either**: it is **undecided**, and one convergent measurement
decides it. The non-stationarity *diagnosis* and the instrument chain survive; the specific per-market
*verdict* does not yet follow from the evidence.

## What survives (foundation sound)
- Non-stationarity inflates n̂ (8–12× ramp) — corroborated by the independent HB mean-variance estimator
  and the per-third analysis; textbook Filimonov–Sornette.
- Instrument chain: μ(t) MLE (10/10 tests); profile-likelihood as the right object (KS proxy caught and
  discarded); clean stream (unique `transaction_hash`).
- **…9076 (35k) provisionally genuine near-critical** — stays interior under grid extension AND recovers a
  planted 0.90. This survives the round.

## Findings (severity-ranked, both arms)

| # | Sev | Finding | Arm |
|---|---|---|---|
| 1 | BLOCKER | Debiased floor map is **non-monotone at market scale**: 18k cell recovers **2/4** (10k=3/4, 14k=4/4), failures are overshoots `[1.05,1.05,…]`. A clean near-critical model false-migrates ~half the time at 18k on a single realization → markets …3503 (18k)/…9630 (22k) degenerating is what a clean-but-unlucky single realization looks like. The "above floor ⇒ mis-modelled" modus tollens collapses on the floor map's own numbers. | both |
| 2 | BLOCKER | **Discriminating composition missing**: grid-extension was never run on the markets'-own-params *genuine* synthetics. `matched_recovery` reports only the fixed-grid peak, not whether a planted-genuine market also migrates at 18–22k. Migration-gate specificity at these N is unmeasured (finding 1 suggests it is poor). | Claude |
| 3 | MAJOR | **…3503's own-params recovery never computed** (excluded — its fit peak is supercritical). "…3503/…9630 PASS step 3's logic" is unsupported for …3503. | ChatGPT |
| 4 | MAJOR | **"Migrates to eps=0.02" is factually wrong**: the jump is at **eps=0.2 and argmax-eps stays 0.2** under further opening. Real statement: "allowing eps=0.2 surfaces a higher-likelihood supercritical mode." Needs an **n<1-constrained variant** to separate finite-window artifact from genuine supercriticality. | ChatGPT |
| 5 | MAJOR | **Calibration covers only the low-n end** (`n_true=0.5`, and peaks **+0.1 high** even there). The **near-critical truth end** — where the markets and the μ(t)↔long-memory-kernel confound (Risk #3) live — was never calibrated. | Claude |
| 6 | MOD | **"Matched" isn't matched**: `mu(t)=mu0(1+ramp·t/T)` ⇒ swing=`1+ramp`, so feeding 9.5/11.7 simulates ~10.5×/12.7×; …9076 synthetic uses N=27,643 vs real 34,830. Report realized N and swing. | ChatGPT |
| 7 | MOD | **n-grid (0.15) coarser than the [0.9,1.0) band (0.10)** — can't place …9076 within the band; headline 0.90 is one grid node. | Claude |
| 8 | MOD | **Gate-D**: grid opened to eps=0.02 *because* markets migrated → gate thresholds outcome-tuned. Freeze on synthetic calibration before the real verdict (measure-before-amending applied to the gate's own knobs). | Claude |
| 9 | MINOR | `mu_t_sweep` plateau detector labels K≈2 a plateau while n̂ descends 0.70→0.36 (superseded stage). | ChatGPT |

## The convergent measurement (both arms independently)
Per-market, run the **full gate on genuine synthetics** at each market's own fitted (eps, c, n), **realized
N**, **corrected ramp units**, **≥8 seeds**, **including grid-extension on those genuine synthetics**; bracket
…3503 with a pre-specified subcritical n (its fit is supercritical/unsimulable); add the n<1-constrained
variant; calibrate at the near-critical end. **One principled run closes findings 1–6**, with thresholds
**frozen on synthetic calibration first** (finding 8) so the verdict is result-blind.

Two outcomes, both real:
- Genuine rarely migrates while real markets migrate decisively → **split earned, "settled" honest.**
- Genuine migrates ~half the time at 18–22k → **near-criticality not resolvable at these N for 2/3** — a
  real Filimonov–Sornette result (reverts toward the resolution-floor reading, now established not asserted).
Either way **…9076 stays provisionally genuine.**

## Decision (reviewer-of-record, 2026-06-22)
Two findings land on the reviewer-of-record directly and are **accepted**: (i) 18k=2/4 is a **blocker**, not
the "noise wobble" the §7 caveat called it — under-powered (4 seeds) but not dismissible; (ii) "grid
extension rescues the per-market noise" was **asserted, not measured** (never run on genuine synthetics).
State is **undecided, not refuted.**

**Accepted action:** record this round (process), then **run the convergent measurement** with gate
thresholds **frozen on synthetic calibration first**. The freeze-then-verdict ordering is the result-blind
safeguard. Recording without running leaves the conclusion in limbo; the n<1-constrained item (finding 4)
alone is narrower than the measurement settles — so neither is the move on its own. Findings 1–6 fold into
the single run.

## Round-2 entry condition
Re-review after the convergent run: does genuine near-critical false-migrate at the markets' realized N? The
measured false-migration rate turns "…9076 provisional" into settled-or-honestly-not-resolvable and decides
the split.
