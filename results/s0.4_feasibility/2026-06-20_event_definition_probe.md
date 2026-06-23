# §4b Event-definition probe — source B (live WS capture)

**Date:** 2026-06-20 · **Branch:** `s0.4-data-feasibility-spike` · **Status:** window-safe pre-freeze input (no `n̂` inspected — Gate D / result-blind).

**Why this exists.** The first contact of the cert harness with the *real* source-B capture flagged
that 81% of one market's `last_trade_price` messages repeat the prior price (`dup_px 559/686`).
That reopened PRE_REGISTRATION §4b (event unit): if a large fraction of messages are *re-emitted
state* rather than trades, every event count is inflated several-fold and every downstream `n̂` and
the floor (denominated in "events") is corrupted. §4b is the unit under the floor and the margins,
so it must be pinned **before** the S0.2 stability sims and the freeze. All probes below are
feed-mechanics facts — no branching ratio inspected — so resolving them now is methodologically free.

**Data.** `~/b_capture/ws_capture.jsonl`, hottest market `…398510133975` (≈687 msgs / ~1.6 h window).

## Findings (measured, not documented)

1. **Message schema.** Every `last_trade_price` message carries:
   `market, asset_id, price, size, fee_rate_bps, side, timestamp(ms), event_type, transaction_hash`.

2. **Re-emission RULED OUT (decisive).**
   - 687 messages → **687 distinct `transaction_hash`** (a fresh on-chain tx per message).
   - same-price-consecutive messages sharing a tx_hash: **0**.
   - distinct `size`/`side` per message (e.g. two `0.05` rows = SELL 1.43 and SELL 2.6, different txs).
   - temporal tell: inter-arrival **CV = 8.86** (bursty/clustered — a re-emit timer would be CV ≪ 1);
     same-price gaps are sub-second and clustered (median 0.141 s), not at a fixed cadence.
   → The 81%-same-price is **genuine trades at a price parked ~0.05–0.06**, not re-emitted state.
   The worst case (over-counting → corrupted `n̂`, markets further from floor than they look) is **off the table**.

3. **Fill-vs-match coincide in source B.** messages / distinct-tx = **1.000**, distribution `{1: 687}`.
   No multi-fill-per-tx aggregation on the WS side. `fill` unit = `tx` unit = 687.

4. **Reader caveat (log, low-priority).** `b_reader.read_markets(event_unit="match")` collapses by
   **ms timestamp**, and the capture already has **1 coincidental same-ms pair of distinct txs**
   (match-by-ms = 686 vs 687 real trades). Ms-collapse would wrongly merge two genuine trades; if
   `match` is ever used it should key on `transaction_hash`. Moot while msgs/tx ≡ 1 — `fill` is correct.

## Decision (source B)

**One event = one `last_trade_price` message = one trade-arrival = one on-chain tx.** `event_unit="fill"`
is correct for B. No re-emission inflation → the floor on the live B capture is denominated in **real
trades**. This pins §4b for the live/load-bearing path; the S0.2 floor/margin sims can now count in a
verified unit.

## Residual (needs on-chain; sequenced after, not racing the window)

**A↔B unit reconciliation.** Source A (`reconstruct.py`) counts `OrderFilled` **fills**
(`n_events = len(fills)`, one-side de-duplicated). Source B counts **trades** (1 msg / tx). One taker
crossing N makers = N `OrderFilled` in **one** tx, so A-counts (fills) can exceed B-counts (trades) for
the same window. A and B must measure the *same* point process for H1c (market-vs-sim) and for
A-historical / B-hedge consistency.

- **Scoped test:** count `OrderFilled` logs per `transaction_hash` for a sample of the captured txs.
- **Access:** A's decoded fills come from **Dune (offsite, currently held)**; the cheap local version
  is a Polygon RPC `eth_getTransactionReceipt` on captured tx_hashes, counting `OrderFilled` logs.
- **Sequencing:** on-chain history is permanent (no data lost by waiting), and B's unit is already
  pinned, so this resolves **before Stage-1 relies on A** — it is not racing the accumulation clock.

## Provenance

Full project test suite green at probe time: **85 passed** (`tests/` + `spike/s0.4/tests/`).
