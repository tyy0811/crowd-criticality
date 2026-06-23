#!/usr/bin/env python3
"""launchd launcher for the Source-B forward capture (Mac), restart-safe with a HARD calendar backstop.

The original start time is persisted in ~/b_capture/start_ts and honored ACROSS launchd crash-restarts,
so the backstop is true wall-clock, not per-restart. Clean exit 0 at the backstop -> launchd (KeepAlive
SuccessfulExit=false) stops; a real crash -> exit 1 -> launchd restarts and the remaining time continues
(the recorder self-reconnects on WS drops, so crashes should be rare).

The backstop is ONLY a runaway guard. The REAL stop is outcome-gated: run capture_status.py and stop
when enough NEAR-CRITICAL markets cross the event floor (sustained yield, not the burst-inflated probe).
"""
import asyncio
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
for _cand in (HERE, HERE.parent):       # deployed (ws_recorder.py alongside, outside TCC) OR in-repo
    if (_cand / "ws_recorder.py").exists():
        sys.path.insert(0, str(_cand))
        break
import ws_recorder                                               # noqa: E402

DATA = pathlib.Path.home() / "b_capture"
DATA.mkdir(exist_ok=True)
OUT = str(DATA / "ws_capture.jsonl")
START = DATA / "start_ts"
BACKSTOP_S = 7 * 86400                                           # calendar backstop only

now = time.time()
start = float(START.read_text().strip()) if START.exists() else now
if not START.exists():
    START.write_text(str(start))
remaining = BACKSTOP_S - (now - start)


def _ts():
    return time.strftime("%Y-%m-%d %H:%M:%S")


if remaining <= 0:
    print(f"[{_ts()}] 7-day backstop reached -> clean stop (launchd will not restart).", flush=True)
    sys.exit(0)

print(f"[{_ts()}] capture -> {OUT} | backstop in {remaining / 3600:.1f}h", flush=True)
try:
    asyncio.run(asyncio.wait_for(ws_recorder.record(OUT, 30, 6.0), timeout=remaining))
except asyncio.TimeoutError:
    print(f"[{_ts()}] backstop reached -> clean stop.", flush=True)
    sys.exit(0)
except Exception as exc:                                         # real crash -> non-zero -> launchd restart
    print(f"[{_ts()}] CRASH {type(exc).__name__}: {exc} -> launchd restart", flush=True)
    sys.exit(1)
sys.exit(0)
