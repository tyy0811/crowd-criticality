"""Source-B forward recorder: capture live Polymarket trades on a basket of open,
short-horizon markets to append-only JSONL, with a LOCAL high-resolution receive timestamp
(sub-second — finer than source A's 2 s block time, though forward-only).

Starting this is the cheap calendar hedge; its resolved-market OUTCOME is calendar-deferred.
Offsite. Requires `websockets` (offsite-only; do NOT add to pyproject). Capture only.

The §6 timestamp-resolution question (does the live feed stamp sub-2 s?) is answered on
inspection of the capture: each line carries `recv_ts` (local, sub-second) AND the full `msg`
(whose own timestamp field, if any, reveals the server-side resolution). No live analysis here.

CONFIRM-AT-RUNTIME (spec §10): the exact CLOB WebSocket URL and message schema.

Run: python spike/s0.4/ws_recorder.py --max-days 30 --out results/s0.4_feasibility/ws_capture.jsonl
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import urllib.request

import websockets  # offsite-only dependency

GAMMA = "https://gamma-api.polymarket.com"
WS_URL = "wss://ws-subscribe-clob.polymarket.com/ws/market"  # CONFIRM at runtime


def select_basket(max_days: int) -> list[str]:
    """Open markets resolving within `max_days`, ordered by recent volume; return token ids."""
    end = time.time() + max_days * 86400
    url = f"{GAMMA}/markets?closed=false&order=volume24hr&ascending=false&limit=50"
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
        markets = json.load(resp)
    token_ids: list[str] = []
    for m in markets:
        end_iso = m.get("endDate")
        if end_iso and time.mktime(time.strptime(end_iso[:19], "%Y-%m-%dT%H:%M:%S")) <= end:
            ids = m.get("clobTokenIds")
            token_ids += json.loads(ids) if isinstance(ids, str) else (ids or [])
    return token_ids


async def record(token_ids: list[str], out_path: str) -> None:
    if not token_ids:
        raise SystemExit("FAIL: empty basket — confirm Gamma filters at runtime")
    async for ws in websockets.connect(WS_URL, ping_interval=20):  # auto-reconnect on drop
        try:
            await ws.send(json.dumps({"type": "market", "assets_ids": token_ids}))
            with open(out_path, "a") as f:
                async for msg in ws:
                    f.write(json.dumps({"recv_ts": time.time(), "msg": json.loads(msg)}) + "\n")
                    f.flush()
        except websockets.ConnectionClosed:
            continue  # reconnect; append-only file is never lost


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-days", type=int, default=30)
    ap.add_argument("--out", default="results/s0.4_feasibility/ws_capture.jsonl")
    a = ap.parse_args()
    asyncio.run(record(select_basket(a.max_days), a.out))
