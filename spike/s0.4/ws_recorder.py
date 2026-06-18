"""Source-B forward recorder: capture LIVE Polymarket trades on a basket of open, short-horizon
markets to append-only JSONL, with a local high-resolution receive timestamp.

Writes ONLY last_trade_price (per-trade) events with their server match timestamp in ms -- the
n-hat signal -- and skips book/price_change (which dominate volume but are not needed for n-hat),
keeping a multi-week capture small. Re-selects the market basket every --refresh-hours so it does
not go stale as markets resolve. Auto-reconnects on WS drop; append-only so a restart loses nothing.
Each last_trade_price event carries its asset_id, so per-market grouping survives basket refreshes.

Offsite. Requires `websockets` (offsite-only; NOT added to pyproject). Capture only -- no analysis.
Run with PYTHON 3 (a bare 'python' may be system Python 2):
    /Users/zenith/anaconda3/bin/python spike/s0.4/ws_recorder.py --out ~/b_capture.jsonl

CONFIRM-AT-RUNTIME: WS URL + schema confirmed 2026-06-18 vs docs.polymarket.com CLOB market channel.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import urllib.request

import websockets  # offsite-only dependency

GAMMA = "https://gamma-api.polymarket.com"
WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"  # documented + live-confirmed
# Polymarket's public APIs 403 the default urllib User-Agent (bot filter); a browser UA clears it.
_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120 Safari/537.36"}


def select_basket(max_days: int) -> list[str]:
    """Open markets resolving within `max_days`, ordered by recent volume; return their token ids."""
    end = time.time() + max_days * 86400
    url = f"{GAMMA}/markets?closed=false&order=volume24hr&ascending=false&limit=50"
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        markets = json.load(resp)
    token_ids: list[str] = []
    for m in markets:
        end_iso = m.get("endDate")
        if end_iso and time.mktime(time.strptime(end_iso[:19], "%Y-%m-%dT%H:%M:%S")) <= end:
            ids = m.get("clobTokenIds")
            token_ids += json.loads(ids) if isinstance(ids, str) else (ids or [])
    return token_ids


async def record(out_path: str, max_days: int, refresh_hours: float) -> None:
    """Append last_trade_price events to JSONL, re-selecting the basket every `refresh_hours`."""
    while True:                                              # basket-refresh loop
        token_ids = select_basket(max_days)
        if not token_ids:
            raise SystemExit("FAIL: empty basket -- confirm Gamma filters at runtime")
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] basket: {len(token_ids)} tokens "
              f"(refresh in {refresh_hours}h)", flush=True)
        deadline = time.time() + refresh_hours * 3600.0
        while time.time() < deadline:                       # reconnect loop, SAME basket
            try:
                async with websockets.connect(WS_URL, ping_interval=20, max_size=None) as ws:
                    await ws.send(json.dumps({"type": "market", "assets_ids": token_ids}))
                    with open(out_path, "a") as f:
                        while time.time() < deadline:
                            raw = await asyncio.wait_for(
                                ws.recv(), timeout=min(60.0, max(1.0, deadline - time.time())))
                            recv_ts = time.time()
                            obj = json.loads(raw)
                            for e in (obj if isinstance(obj, list) else [obj]):
                                if isinstance(e, dict) and e.get("event_type") == "last_trade_price":
                                    f.write(json.dumps({"recv_ts": recv_ts, "msg": e}) + "\n")
                            f.flush()
            except (websockets.ConnectionClosed, asyncio.TimeoutError, OSError) as exc:
                print(f"[{time.strftime('%H:%M:%S')}] reconnect ({type(exc).__name__})", flush=True)
                await asyncio.sleep(2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-days", type=int, default=30)
    ap.add_argument("--out", default="results/s0.4_feasibility/ws_capture.jsonl")
    ap.add_argument("--refresh-hours", type=float, default=6.0)
    a = ap.parse_args()
    asyncio.run(record(a.out, a.max_days, a.refresh_hours))
