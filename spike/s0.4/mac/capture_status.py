#!/usr/bin/env python3
"""Outcome monitor for the live Source-B capture -- the BINDING quantities, not total volume.

Per market: event count, SUSTAINED rate (events / elapsed-hour, NOT burst), a provisional n-hat
(UNCERTIFIED -- assumes a plausible Lomax shape), a near-critical flag, and time-to-floor. The question
that gates the stop is: how many NEAR-CRITICAL markets are on track to cross the event floor -- because
near-critical markets are bursty, their sustained yield (here, not the probe) is what decides feasibility.

    /Users/zenith/anaconda3/bin/python spike/s0.4/mac/capture_status.py
"""
import pathlib
import sys
import time

SPIKE = pathlib.Path(__file__).resolve().parent.parent          # spike/s0.4
sys.path.insert(0, str(SPIKE))
from b_reader import read_markets                                # noqa: E402
from critaudit.hawkes.binned import PowerLawKernel, fit_full     # noqa: E402

DATA = pathlib.Path.home() / "b_capture"
OUT = str(DATA / "ws_capture.jsonl")
START = DATA / "start_ts"
FLOOR = 16_000          # provisional GoF-power floor (a FLOOR; subtler shape errors need MORE)
FIT_MIN = 400           # min events before a provisional n-hat is meaningful
EPS, C = 0.4, 0.5       # provisional assumed Lomax shape (the real cert GoF-gates this)
CRIT = 0.8              # n-hat above this = near-critical, watch

k = PowerLawKernel(eps=EPS, c=C)
markets = read_markets(OUT)
elapsed_h = (time.time() - float(START.read_text())) / 3600 if START.exists() else float("nan")
markets.sort(key=lambda m: -m.n_events)

print(f"capture: {len(markets)} markets | elapsed {elapsed_h:.1f}h | floor {FLOOR} (provisional)")
print(f"{'asset(tail)':>14} {'events':>8} {'ev/h':>7} {'n_hat':>6} {'crit':>4} {'to_floor_h':>10}")
n_over = n_crit = n_track = 0
for m in markets[:15]:
    rate = m.n_events / elapsed_h if elapsed_h > 0 else float("nan")
    nh = fit_full(m.times, m.horizon, k)[1] if m.n_events >= FIT_MIN else float("nan")
    crit = nh == nh and nh > CRIT
    over = m.n_events >= FLOOR
    tof = 0.0 if over else ((FLOOR - m.n_events) / rate if rate > 0 else float("inf"))
    n_over += int(over)
    n_crit += int(crit)
    n_track += int(crit and (over or tof < 7 * 24))
    print(f"{m.asset_id[-12:]:>14} {m.n_events:>8} {rate:>7.0f} {nh:>6.2f} "
          f"{'YES' if crit else '':>4} {tof:>10.1f}")
print(f"\nat/over floor: {n_over} | near-critical (n_hat>{CRIT}): {n_crit} | "
      f"on track within backstop: {n_track}")
print("provisional n_hat is UNCERTIFIED (assumes a Lomax shape); run certify_capture for the "
      "GoF-gated verdict on the accumulated day.")
