"""Source-B JSONL reader: parse ws_recorder.py output into per-market, zero-based, SECONDS event-time
arrays for certify_granularity / the real-data cert driver.

The n̂ signal is the server match timestamp msg["timestamp"] (ms); recv_ts is local, diagnostics-only.
Times are zero-based per market (histogram bins start at 0). Ties (same-ms fills) are KEPT under
event_unit="fill"; event_unit="match" collapses same-(asset, ms) fills into one event. Diagnostics
(multiplicity, tied count, consecutive dup-price) are always reported at FILL level and drive the
fill-vs-match event-unit decision.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np


@dataclass
class MarketEvents:
    asset_id: str
    times: np.ndarray            # sorted, seconds, zero-based
    horizon: float               # = times.max() (span); times in [0, horizon]
    t0_unix_s: float             # window origin (min server ts), seconds
    n_events: int
    max_ms_multiplicity: int     # largest # of fills sharing one (asset, ms)
    n_tied_events: int           # fills sharing a ms with >=1 other
    n_dup_price_consecutive: int # consecutive same-price fills (confirms per-fill emission)


def _clean_window(recv_ts, sleep_gap_s):
    """Bounds (lo, hi) of the longest-by-event-count contiguous run of recv_ts with no internal gap
    exceeding sleep_gap_s. A lid-sleep / recorder outage is a capture-wide recv_ts gap (no events
    received across the whole basket at once), so the surviving run is a continuous-observation window.
    Returns (None, None) for empty input."""
    r = np.sort(np.asarray(recv_ts, dtype=float))
    if r.size == 0:
        return None, None
    if r.size == 1:
        return float(r[0]), float(r[0])
    breaks = np.where(np.diff(r) > sleep_gap_s)[0]          # gap AFTER index i -> segment boundary
    starts = np.concatenate([[0], breaks + 1])
    ends = np.concatenate([breaks, [r.size - 1]])
    j = int(np.argmax(ends - starts))                       # most events (ties -> earliest segment)
    return float(r[starts[j]]), float(r[ends[j]])


def read_markets(path, *, event_unit="fill", sleep_gap_s=None):
    """Parse B-JSONL into per-market MarketEvents.

    event_unit: "fill" keeps every last_trade_price; "match" collapses fills sharing an identical
    (asset_id, ms-timestamp) into one event.
    sleep_gap_s: if set, drop events outside the longest gap-free recv_ts window (excludes lid-sleep /
    outage periods whose artificial quiet would bias n̂ downward); None = keep everything."""
    if event_unit not in ("fill", "match"):
        raise ValueError(f"event_unit must be 'fill' or 'match', got {event_unit!r}")

    by_asset: dict[str, list] = {}
    bad = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()              # handles CRLF + trailing whitespace
            if not line:
                continue
            try:
                obj = json.loads(line)
                msg = obj["msg"]
            except (json.JSONDecodeError, KeyError, TypeError):
                bad += 1
                continue
            if not isinstance(msg, dict) or msg.get("event_type") != "last_trade_price":
                continue
            try:
                ts_ms = int(float(msg["timestamp"]))
                asset = msg["asset_id"]
                if not isinstance(asset, str):       # non-string -> unhashable dict key risk; skip
                    raise TypeError("asset_id must be a string")
            except (KeyError, TypeError, ValueError, OverflowError):  # OverflowError: int(float("1e999"))
                bad += 1
                continue
            recv = obj.get("recv_ts") if isinstance(obj, dict) else None
            by_asset.setdefault(asset, []).append((ts_ms, msg.get("price"), recv))
    if bad:
        print(f"b_reader: skipped {bad} unparseable/incomplete line(s)")

    if sleep_gap_s is not None:
        all_recv = [r[2] for rows in by_asset.values() for r in rows if r[2] is not None]
        lo, hi = _clean_window(all_recv, sleep_gap_s) if all_recv else (None, None)
        if lo is not None:
            kept, dropped = {}, 0
            for asset, rows in by_asset.items():
                keep = [r for r in rows if r[2] is not None and lo <= r[2] <= hi]
                dropped += len(rows) - len(keep)
                if keep:
                    kept[asset] = keep
            if dropped:
                print(f"b_reader: sleep-gap guard kept recv_ts window [{lo:.0f}, {hi:.0f}] "
                      f"({hi - lo:.0f}s); dropped {dropped} event(s) outside it")
            by_asset = kept

    markets = []
    for asset, rows in by_asset.items():
        rows.sort(key=lambda r: r[0])
        ts = np.array([r[0] for r in rows], dtype=np.int64)
        prices = [r[1] for r in rows]
        uniq, counts = np.unique(ts, return_counts=True)
        max_mult = int(counts.max())
        n_tied = int(counts[counts > 1].sum())
        dup_price = sum(1 for i in range(1, len(prices))
                        if prices[i] is not None and prices[i] == prices[i - 1])
        if event_unit == "match":
            ts = uniq
        t0_ms = int(ts[0])
        times = (ts - t0_ms) / 1000.0
        markets.append(MarketEvents(
            asset_id=asset, times=times, horizon=float(times[-1]),
            t0_unix_s=t0_ms / 1000.0, n_events=int(times.size),
            max_ms_multiplicity=max_mult, n_tied_events=n_tied,
            n_dup_price_consecutive=dup_price))
    return markets
