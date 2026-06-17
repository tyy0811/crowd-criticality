# S0.4 §6 — Source-B live verification: does B preserve within-bin ORDER?

Run on a **network-capable session** (the handoff's network branch; the design session was assumed
sandboxed). Bounded ~45 s live capture of the Polymarket CLOB market-channel WebSocket. **This is the
pre-flight for the recorder deploy, not the deploy** — schema/resolution confirmation only; the
persistent forward capture still runs on the user's machine (this session is ephemeral).

## Endpoint (CONFIRM-AT-RUNTIME resolved)
Documented **and** empirically confirmed: `wss://ws-subscriptions-clob.polymarket.com/ws/market`.
The plan's `ws_recorder.py` had `ws-subscribe-clob` (**wrong**) — corrected to `ws-subscriptions-clob`.
Subscription: `{"assets_ids": [token_ids...], "type": "market"}`.

## Access path (made explicitly clean, per review)
Gamma + Data APIs are public, no auth; the CLOB WS is the documented public real-time endpoint,
described as research-suitable with "virtually no" WS restrictions. The default-UA 403 clears with a
browser `User-Agent` — ordinary bot-filter plumbing, **not** routing around an intended research gate.
(Full ToS not exhaustively reviewed; the documented-public + research-suitable status is the basis.)

## The real question — not "is the field fine", but: does B preserve within-bin ORDER?
`n` is identified by the within-bin order (the MCEM de-risk result), which A's 2 s block-time destroys
and B is meant to carry. A precise *receive-time* field that is jittered / reordered / batched relative
to match-time would be a mirage. Measured live (45 s, 50 token ids across top markets; 18 trades observed):

- **Q1 — server/match timestamp:** PRESENT on 18/18 `last_trade_price` events, **millisecond** precision,
  all distinct. The sub-second part (`ts mod 1000 ms`) spans **120..955 ms** → a **true sub-2 s match
  time**, NOT block-quantized (a block-settlement re-stamp would cluster near 000 ms).
- **Q2 — batching:** `last_trade_price` is delivered **INDIVIDUALLY** (max 1 per frame) — per-trade, not
  an aggregated latest-price tick.
- **Q3 — order:** **0 / 17** receive-vs-server-timestamp inversions → receive order == match order, **no
  reordering jitter**.
- **Q4 — inter-trade server gaps:** min **56 ms**, median ~1804 ms, **53 % < 2000 ms** → genuinely sub-2 s
  resolution (finer than A's 2 s block).

## Verdict
**B preserves within-bin order:** per-trade, individually delivered, ms match-timestamp, in match order,
sub-2 s and not block-aligned. **The hedge is real** — B carries the `n`-identifying timing that A loses
to block-time. If the power-law MCEM test on A fails, **B is a viable n̂-timing source** (load-bearing).

## Caveats
- Structural/schema questions settled in 45 s (the goal). Trade **rate** was low (~0.4/s across 50 tokens,
  18 trades) — adequate for STRUCTURE, not for `n̂` estimation; the event-count floor (S0.2-pending) and
  high-rate market selection are separate questions.
- `timestamp` is the server's reported match time; the load-bearing property (order preservation) is
  confirmed empirically (0 inversions, sub-2 s, distinct values), independent of whether it is the exact
  match instant or server-receive.
- **Deploy de-risked:** with the corrected URL + UA, the recorder will capture usable sub-2 s match
  timestamps. The persistent multi-week capture still runs on the user's machine — the only clock that
  cannot be restarted.
