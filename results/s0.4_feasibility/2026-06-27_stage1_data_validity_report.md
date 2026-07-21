# Reconstructing Polymarket microstructure: a data-validity study of per-market criticality at achievable event counts

**Date:** 2026-06-27 · **Status:** Stage-1 data-validity deliverable (the `PRE_REGISTRATION.md`/`IMPLEMENTATION_PLAN.md` gate-fails artifact). Written for a reader without project context.

> **Repository archive status: retrospective (2026-07-22).** This report and its five June 25–26 supporting rule/result records remained uncommitted in the owner's working tree until the plan-reconciliation archive commit. Their dated text records the operator's stated chronology, but the files' relative history **does not provide git-visible freeze-before-measure evidence**. The committed 2026-06-22 `DECISIONS.md` trail does document the earlier identifiability arc's prospective synthetic-first calibration; that narrower evidence is not extended to the later uncommitted records. The numbers and scientific scope below are unchanged. **No trustworthy per-market `n` is banked.**

---

## Abstract

We attempt to certify branching-ratio near-criticality on live Polymarket prediction-market trade streams, captured at sub-second resolution. The central result is negative and narrow, and it is established by two independent instruments under result-blind, pre-frozen criteria:

> **On this venue, per-market near-criticality is not cleanly certifiable at the achievable event counts.** A fixed-shape power-law Hawkes goodness-of-fit rejects the assumed kernel on **0 of 9** over-floor markets (all at the bootstrap floor value), and an independent flexible-baseline μ(t) identifiability gate measures a per-market false-migration rate of **15–27%** for genuine near-critical processes at 18–35k events. The rejection is isolated to the venue's **non-stationarity** (markets ramp 8–12× toward resolution), demonstrated robust to data volume, robust to de-burstification, and — most diagnostically — *hardening* with observation-window duration.

The cohort number that anchors the claim (how many markets have enough clean data to assess) is shown robust to every instrument that could have inflated or deflated it. A by-product of the capture is a validated recapture design — dual independent recorders merged by transaction hash — that collapses WebSocket fragmentation and is separately reusable.

The narrow scope is load-bearing: this is a statement about the **fixed-shape** fit on **this venue's** over-floor cohort. It is **not** "prediction markets are not critical" and **not** "Hawkes processes do not fit prediction-market data."

---

## 1. Background and the object of measurement

The branching ratio `n` of a self-exciting (Hawkes) point process measures endogenous reflexivity: the expected number of events directly triggered by a given event. `n → 1` is the critical point. Financial markets sit near `n ≈ 1` on HFT data (Hardiman–Bercot–Bouchaud 2013), and the Filimonov–Sornette critique warns that a non-stationary baseline can inflate the *apparent* `n` toward 1 even when the true endogenous reflexivity is low. Prediction markets are an unstudied venue for this question and, unlike HFT order flow, expose a clean per-market event stream.

The certifiable object is a per-market `n̂` with its associated avalanche exponents. To trust a per-market `n̂` we require both (a) **enough clean events** to fit (an empirical floor, established by synthetic recovery at ~16k events — below this the estimator is under-resolved), and (b) the fitted model to **survive a goodness-of-fit gate** — a power law that only looks critical under a constant baseline, or under a misspecified kernel shape, is rejected.

This report covers the data-validity arc: whether the data exists at the needed quality, and whether the over-floor markets certify.

## 2. The finding (precise scope)

Two independent instruments, each with criteria frozen before the data they judged, reach a consistent negative conclusion:

**Instrument A — fixed-shape goodness-of-fit (this report's spine).** A KS time-rescaling (Ogata random-time-change) test of the inter-event intervals against `Exp(1)`, calibrated by a B=199 parametric bootstrap from the fitted `(μ, n)` under a fixed power-law (Lomax) kernel `eps=0.4, c=0.5`; a market certifies iff `p_boot ≥ 0.10`. **Result: 0 of 9 over-floor markets certify** — every one at the bootstrap floor value `p_boot=0.0050`. The misfit is sizeable, not marginal: the first certified market's `D_obs=0.0644` is ≈8× the `~1/√N ≈ 0.0075` a correct fit would give.

**Instrument B — flexible-baseline μ(t) identifiability gate (prior, companion).** A grid-extension + matched-recovery gate using a piecewise-constant μ(t) baseline and profile likelihood over `n`. It measures whether a *genuine* near-critical (`n=0.90`) process, simulated at each market's own realized regime, false-migrates to a supercritical estimate. **Result: a measured per-market false-migration rate of 15–27% at 18–35k events**, with no firm improvement through 100k (a roughly flat 7–17% floor across the achievable range). The real markets' migration peaks sit *inside* the genuine near-critical upper tail (own-regime 93rd–95th percentile), not beyond it — i.e. indistinguishable from genuine-near-critical-the-instrument-cannot-resolve. (Full arc: `2026-06-23_per_market_criticality_DELIVERABLE.md`.)

The two instruments fail for **different reasons** — Instrument A on the kernel *shape*, Instrument B on *identifiability* of `n̂` — and their agreement is mutual corroboration, not redundancy: per-market near-criticality on this venue resists certification both because the assumed shape does not fit and because the achievable counts cannot separate genuine near-critical from apparent.

## 3. The data: dual independent capture, same-feed validated

Capture used two **independent** recorders on the Polymarket CLOB WebSocket `last_trade_price` feed, running in parallel on the same machine for 5–7 days:

| stream | started | unique events | recv-time span |
|---|---|---|---|
| A | 2026-06-20 | 818,625 | 131.1 h |
| B | 2026-06-18 | 921,869 | 168.8 h |

The scientific timing signal is the **server match timestamp** (`msg["timestamp"]`), identical across both recorders for the same trade, so the capturing process is neutral. Trades are keyed by on-chain `transaction_hash`.

**Same-feed validity gate (prerequisite for any merge).** Of 784,509 transaction hashes present in *both* streams, field mismatches on `(asset_id, server-timestamp, size)` are **0 / 0 / 0**. The two recorders record the same trades; their union is a valid denser capture. Their outages are genuinely independent: A captured 34,116 hashes B missed, B captured 137,360 A missed.

## 4. The instrument arc — the cohort number is robust to every instrument that could move it

The headline is `0/9`, but the credibility is in the sequence: each instrument either inflated or deflated the assessable-cohort number, and each was overturned by the next *by resolution, not argument*. The final number survived the hardest stress the data could mount.

| step | instrument | assessable cohort | what it established |
|---|---|---|---|
| 1 | raw event count (no gap guard) | **9** "over floor" | looked like a healthy cohort |
| 2 | gap-guard (longest gap-free window, 60 s outage def.) | **3** | single-capture fragmentation: longest clean window 31 h, 72% of events dropped; the raw 9 was a fragmentation artifact |
| 3 | per-market largest-fragment screen + fixed-shape GoF | **3** confirmed; 2 burst-survivors → **0/2** certify | single capture genuinely caps at 3, and even the 2 salvageable bursts reject |
| 4 | dual-capture merge (independent outages filled) | **9** (6 NEW) | merge collapses fragmentation (31 h window → 55 both-out gaps over 7 days); raises the *assessable* cohort back to 9 |
| 5 | fixed-shape GoF on the merged cohort | **0/9** certify | the assessable cohort is 9; **none certify** |

Two points this arc nails down. First, **"assessable" ≠ "certified."** The "3" and "9" are markets with enough clean data to *run* the gate on; the certified count was always **0** (the original 3 themselves reject — the locked 0/3). The merge raised the *assessable* cohort 3→9; the certified count is 0/9. Second, the merge did exactly what it was built for (recover clean windows) and the cohort still certified 0 — so the ceiling on certifiable markets is **not** fragmentation, burst-domination, or data quantity. That isolation is the report's main analytical move.

## 5. The fixed-shape GoF result: 0/9, uniform

All nine over-floor markets reject at the bootstrap floor `p_boot=0.0050` (i.e. 0 of 199 bootstrap replicates were as extreme as the data). The result is **perfectly uniform** — no market above the floor value — so "systematic" is airtight, with no anomalous market to qualify it.

| market | events | window | `n_fit` (provisional) | `D_obs` | `p_boot` | verdict |
|---|---|---|---|---|---|---|
| …9076918150 | 34830 | single | 0.876 | 0.0516 | 0.005 | FLAGGED |
| …9630680686 | 22089 | single | 0.770 | 0.0966 | 0.005 | FLAGGED |
| …3503937838 | 18019 | 9.1 h, single | 0.772 | 0.0644 | 0.005 | FLAGGED |
| …3510801128 | 21105 | 5.6 h, merged | 0.822 | 0.0390 | 0.005 | FLAGGED |
| …4890691197 | 21748 | 12.5 h, merged | 0.866 | 0.0516 | 0.005 | FLAGGED |
| …6814257223 | 29503 | 25.3 h, merged | 0.903 | 0.0822 | 0.005 | FLAGGED |
| …4676130340 | 20813 | 12.1 h, merged | 0.828 | 0.0677 | 0.005 | FLAGGED |
| …6915180001 | 16692 | 14.2 h, merged | 0.730 | 0.0731 | 0.005 | FLAGGED |
| …5770559698 | 16560 | 11.3 h, merged | 0.851 | 0.0629 | 0.005 | FLAGGED |

(`n_fit` near-critical-looking but provisional — fit under the rejected shape; `D_obs` is the KS time-rescaling statistic, ≈8× the correct-fit `~1/√N` at these N. The two single-window clean3 markets `…9076/…9630` were certified on their single-capture clean windows; the other seven on merged fragments — see §6 for why the window length matters.)

The `n_fit` values are near-critical-looking (0.73–0.90) but **provisional and untrustworthy**: each is fit *under a shape the same test rejects*. The data shows real prediction markets exhibit high *apparent* reflexivity, with the precise value not certifiable — the Filimonov–Sornette apparent-vs-genuine distinction, on a fresh non-HFT venue.

## 6. Why trust it: four corroborations that the cause is non-stationarity

The merge let us hand individual markets progressively *better* data and watch the rejection survive — four independent corroborations, all pointing at the venue's time-structure (the ramp toward resolution) rather than at insufficient or noisy data.

1. **Hardens with duration (the mechanism-identifying one).** Across the seven markets whose clean-window length is resolved, `D_obs` *rises with it* — from **0.039 at 5.6 h** to **0.082 at 25.3 h** (`…6814257223`, 29.5k events, the longest merged fragment). The two single-window clean3 markets carry misfits in the same elevated band (`…9076` 0.052, `…9630` 0.097 — the latter the cohort maximum). A longer window integrates *more* of the resolution ramp, so the stationary-shape fit gets *worse*. This is the direct signature of non-stationarity accumulating over the observation window, and it closes the "why does this venue resist the fit" question: it is the time-structure, not the data. *(The relationship is presently 7 points with resolved window lengths plus 2 in-band; computing the two clean3 window lengths would complete it to a clean 9-point duration relationship — a cheap follow-up if the corroboration is to be quoted quantitatively.)*
2. **Robust to volume.** The merge added clean events to every recovered market; they still reject. More data does not help.
3. **Robust to de-burstification.** The two single-capture survivors were 4 h bursts; the merge converted them to proper multi-hour windows (`…4890691197`: 4.3 h → 12.5 h). They still reject — so the failure is not burst-domination, which the merge removed.
4. **n̂ drifts down with more clean data** (`0.907 → 0.866`, `0.858 → 0.822`). Consistent corroboration: more data partially absorbs the non-stationarity, pulling `n̂` toward its true lower value, while the stationary shape still misfits — exactly what "the rejection is about shape, not volume" predicts.

Four consistent pieces all pointing at non-stationarity-as-cause is what makes the characterization sharp rather than a bare null.

## 7. Methods contribution: dual independent recorders + transaction-hash merge

The arc produced a reusable capture technique, independent of the certification outcome. A single WebSocket recorder fragments badly under connection churn: here, the longest single-recorder gap-free window was only **31 h out of 5+ days**, dropping 72% of events to outage-bounded fragments. Two **independent** recorders on the same feed have largely **uncorrelated** outages (Section 3), so their union by `transaction_hash` collapses the fragmentation: the merged stream has only **55 both-out gaps over 7 days**.

This is a transferable answer to a problem anyone capturing a live prediction-market (or similar) feed will hit. The frozen merge rule (`2026-06-25_dual_capture_merge_rule.md`) is:
- **Validity gate:** require zero `(asset, server-timestamp, size)` mismatches on shared hashes before merging.
- **Event set:** union by `transaction_hash`; fit-time is the server timestamp (identical across copies, so the dedup tie-break cannot move the certified timeline; the tie-break — earlier `recv_ts` — applies only to a degenerate same-feed-violation case and is surfaced if it occurs).
- **Merged-stream gap:** a >60 s interval with **no** `recv_ts` from *either* stream (un-deduped recv union — a trade received by both is doubly-confirmed coverage).

That this technique *worked* (collapsed fragmentation) while the cohort still certified `0/9` is itself the cleanest demonstration that the certification ceiling is not a capture artifact.

## 8. Scope, what is and is not established, limitations

**Established (robust, narrow):**
- The **fixed** Lomax shape (`eps=0.4, c=0.5`) is decisively rejected for all 9 over-floor markets on this venue — bootstrap-confirmed, gap-guarded, tie-robust, uniform.
- The cause is the venue's **non-stationarity** (resolution ramp), isolated by the duration-hardening signature and three further corroborations; it is not fragmentation, burst-domination, or data quantity.
- Independently, the μ(t) identifiability gate measures a 15–27% per-market false-migration floor at 18–35k that does not clear through 100k.

**NOT established (explicit, to resist over-compression):**
- **Not** "prediction markets are not critical." The markets show high *apparent* reflexivity; the precise `n̂` is simply not certifiable here.
- **Not** "Hawkes/Lomax does not fit prediction-market data." The GoF holds the shape *fixed*. Whether a **freely fitted** `(eps, c)` — or any power-law-family shape with a non-stationary baseline — would pass is **untested** (the `H1` wrong-fixed-shape vs `H2` family-wrong question). The natural next instrument is a free-shape fit with a time-varying baseline; the project currently holds it, because the non-stationarity finding indicates the productive fix is a μ(t)/windowed baseline rather than a different stationary shape, and the markets are mild enough (peaks at 1.125, inside the genuine range) not to demand a richer kernel.
- **Single-venue** (Polymarket), **N=9 over-floor markets**, sub-second trade-arrival events. The non-stationarity is a property of resolution-bounded prediction markets specifically.

**Limitation for the wider project:** this constrains the H1c transfer test (consistency of a simulated crowd's optimal `n` with a *trustworthy* real-market `n`), since no per-market `n̂` certifies. H1c was pre-registered as *qualifying* the criticality-optimizes-forecasting claim, not falsifying it; the headline is tested primarily in the simulation arm, with the real market as anchor, not load-bearing test.

## 9. Rule provenance and archive limitation

The table below preserves the operator's dated rule-to-result chronology. The June 22 identifiability decision has prospective support in committed history. The June 25–27 rule/result files, however, were first committed together in the retrospective 2026-07-22 archive, so git history does **not** independently prove their stated freeze-before-measure ordering. They are retained as an auditable operational record, not represented as the document-level analogue of a frozen global pre-registration.

| frozen rule | value | frozen in | judged |
|---|---|---|---|
| event-count floor | 16,000 events | synthetic recovery (pre-capture) | which markets are assessable |
| gap-guard / outage def. | >60 s recv-gap | `b_reader` (pre-capture) | single-capture clean windows |
| fixed-shape GoF | KS-rescaling, `eps=0.4/c=0.5`, B=199, `p_boot ≥ 0.10` | `realdata_cert.py` (pre-first-GoF) | all 9 markets (0/9) |
| μ(t) migration gate + false-migration baseline | (Phase-A locked before Phase-B) | `2026-06-22` DECISIONS + arc | the 15–27% floor |
| fragment-salvage rule (necessary, not sufficient) | per-market largest fragment ≥ 16k, same 60 s | `2026-06-25_fragment_salvage_rule.md` | the 6 dropped markets |
| dual-capture merge rule + merged-gap | union by txhash; >60 s both-out | `2026-06-25_dual_capture_merge_rule.md` | the merged cohort |

The two-stage **necessary-then-sufficient** structure was load-bearing twice: a market clearing the clean-event floor is "assessable," not "certified"; the GoF is the sufficient test, and it killed the single-capture salvage (0/2) and the merged cohort (0/9) on markets that had cleared the floor. The cohort number could be moved only by data, never by a decision.

## 10. Forward

This is the Stage-1 deliverable the plan specifies for the gate-fails branch — a sharp, measured characterization of *why* this venue resists per-market criticality certification, with a reusable capture method, rather than a forced `n̂` paper. It does not block the project: the headline dynamical-class claim is tested in the simulation arm (the LLM-agent crowd and its controls), where the real-market result is the transfer anchor.

Two threads remain logged, not pursued: the free-shape `(eps, c)` / μ(t)-windowed fit that would distinguish `H1` from `H2`; and, if a future Stage-3 resolution sample needs clean capture at scale, the dual-recorder-merge design demonstrated here is the resolved form of that precondition.

---

### Source records (provenance)
`2026-06-21_first_realdata_gof.md` · `2026-06-21_overfloor_passrate.md` · `2026-06-23_per_market_criticality_DELIVERABLE.md` · `2026-06-25_fragment_salvage_rule.md` · `2026-06-25_fragment_salvage_gof.md` · `2026-06-25_dual_capture_merge_rule.md` · `2026-06-26_dual_capture_gof_1128_1197.md` · `2026-06-26_dual_capture_gof_7223_0340_0001_9698.md` · `DECISIONS.md` (2026-06-22 real-data arc) · cert: `spike/s0.4/realdata_cert.py`.
