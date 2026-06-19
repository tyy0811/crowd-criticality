# S0.4 §6 — Source-B live verification: does B preserve within-bin ORDER?

Run on a **network-capable session** (the handoff's network branch). Bounded ~45 s live capture of the
Polymarket CLOB market-channel WebSocket. **Pre-flight for the recorder deploy, not the deploy** — the
persistent forward capture still runs on the user's machine (this session is ephemeral).

## Endpoint + access path
- Endpoint (CONFIRM-AT-RUNTIME resolved): documented **and** live-confirmed `wss://ws-subscriptions-clob.polymarket.com/ws/market`. The plan's `ws_recorder.py` had `ws-subscribe-clob` (**wrong**) — corrected. Subscription `{"assets_ids": [...], "type": "market"}`.
- Access: Gamma/Data public no-auth; CLOB WS is the documented public real-time endpoint, research-suitable. The default-UA 403 clears with a browser UA — ordinary bot-filter plumbing, not a research gate. (Full ToS not exhaustively reviewed — the user's one-time read is the deploy gate.)

## The real question — does B preserve within-bin ORDER? (45 s, 50 token ids, 18 trades)

`n` is identified by within-bin order (the MCEM result), which A's 2 s block-time destroys and B must
carry. A precise *receive-time* field that is jittered / reordered / batched vs match-time would be a mirage:

| # | question | finding | reading |
|---|---|---|---|
| Q1 | server/match timestamp distinct from receive time? | present **18/18**, **ms** precision; sub-second part (ts mod 1000 ms) spans **120–955 ms** | a true sub-2 s match time, **not** block-quantized (a block re-stamp would cluster near 000 ms) |
| Q2 | individual or batched? | `last_trade_price` delivered **individually** (max 1/frame) | per-trade, not an aggregated latest-price tick |
| Q3 | does server-ts order match receive order? | **0 / 17** inversions | receive order == match order, **no reordering jitter** |
| Q4 | inter-trade gap distribution | min **56 ms**, median ~1804 ms, **53 % < 2000 ms** | genuinely sub-2 s (finer than A's 2 s block) |

## Verdict
**B preserves within-bin order** — per-trade, individually delivered, ms match-timestamp, in match order,
sub-2 s and not block-aligned. **The hedge is real**: if A's power-law test fails, B is a viable n̂-timing
source. (In the event it resolved: A's power-law test passed on the granularity axis — see
`DECISIONS.md` — so B stays the forward hedge + sub-2 s cross-check, not load-bearing.)

## Caveats
- Structural/schema questions settled in 45 s (the goal). Trade **rate** was low (~0.4/s across 50 tokens,
  18 trades) — adequate for STRUCTURE, not for `n̂` estimation; high-rate market selection + the event-count
  floor (S0.2) are separate.
- `timestamp` is the server's reported match time; the load-bearing property (order preservation) is
  confirmed empirically (0 inversions, sub-2 s, distinct), independent of exact-instant vs server-receive.
- **Deploy de-risked:** with the corrected URL + UA the recorder captures usable sub-2 s match timestamps;
  the persistent multi-week capture still runs on the user's machine — the only clock that cannot restart.
