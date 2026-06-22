#!/usr/bin/env python3
"""First REAL GoF-gated certification of one captured market -- the divergent-unknown test:
does real near-critical sub-2s trade dynamics match the assumed Lomax-Hawkes SHAPE?

Runs the bootstrap-calibrated goodness-of-fit gate (the scientific heart of certify_market) on the
gap-guarded capture. The granularity-diff step (certify_granularity / MCEM) is DEFERRED: it is
O(N^2 * M) per sweep and intractable at the >=16k events the GoF-power floor requires -- a real
design tension to resolve separately, not to run on faith. Writes a dated verdict file.

    /Users/zenith/anaconda3/bin/python spike/s0.4/mac/certify_one.py
"""
import pathlib
import sys
import time

SPIKE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPIKE))
import numpy as np
from b_reader import read_markets
from critaudit.hawkes.binned import PowerLawKernel, fit_full
from realdata_cert import goodness_of_fit

OUT = "/Users/zenith/b_capture/ws_capture.jsonl"
RESULTS = SPIKE.parent.parent / "results" / "s0.4_feasibility"
EPS, C, GRID = 0.4, 0.5, 2.0          # assumed Lomax shape (the GoF tests THIS) + source-A grid
FLOOR, B, P_FLAG = 16000, 199, 0.10
SLEEP_GAP_S = 60.0
k = PowerLawKernel(eps=EPS, c=C)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


log(f"reading {OUT} (sleep-gap guard {SLEEP_GAP_S}s)")
mk = read_markets(OUT, sleep_gap_s=SLEEP_GAP_S)
over = sorted((m for m in mk if m.n_events >= FLOOR), key=lambda m: m.n_events)
if not over:
    log("no market over floor after guard -- abort")
    sys.exit(1)
m = over[0]                            # smallest over-floor = cheapest O(N^2) first cert
log(f"chosen ...{m.asset_id[-10:]}  N={m.n_events}  horizon={m.horizon:.0f}s")

mu, n = fit_full(m.times, m.horizon, k)
log(f"fit_full: mu={mu:.4f}  n={n:.4f}  (assumed eps={EPS}, c={C})")
log(f"running GoF gate: B={B}, p_flag={P_FLAG}  (~1 min/rep-scale -> tens of min)")
t0 = time.time()
gof = goodness_of_fit(m.times, mu, n, k, np.random.default_rng(0), B=B, p_flag=P_FLAG)
dt = time.time() - t0

if not np.isfinite(gof.p_boot):
    status = "inconclusive (b_eff too low)"
elif gof.passed:
    status = "GoF PASSED -> shape consistent (granularity-diff step deferred: MCEM intractable at this N)"
else:
    status = "FLAGGED shape misfit -> assumed Lomax shape rejected"

verdict = f"""# First real GoF-gated certification -- {time.strftime('%Y-%m-%d %H:%M:%S')}

market:        ...{m.asset_id[-10:]}  (full asset_id {m.asset_id})
N (guarded):   {m.n_events}
horizon:       {m.horizon:.0f} s  ({m.horizon/3600:.1f} h)
assumed shape: PowerLawKernel(eps={EPS}, c={C})  | grid {GRID}s
fit:           mu={mu:.4f}  n={n:.4f}
GoF:           D_obs={gof.stat:.4f}  p_plain={gof.p_plain:.3f}  p_boot={gof.p_boot:.4f}  b_eff={gof.b_eff}/{B}
runtime:       {dt/60:.1f} min

VERDICT: {status}

Notes:
- p_boot is the bootstrap-CALIBRATED gate (p_plain is the anticonservative plain-KS diagnostic).
- n is provisional vs the ASSUMED shape; GoF tests whether that shape is admissible.
- Sleep-gap guard applied (recv_ts window), excluding the 2026-06-20 lid-sleep period.
- Granularity diff (n_binned vs n_full) NOT computed: certify_granularity MCEM is O(N^2*M)/sweep,
  intractable at N>=16k (the GoF-power floor). Resolve as a separate estimator-scaling task.
"""
out = RESULTS / f"{time.strftime('%Y-%m-%d')}_first_realdata_gof.md"
out.write_text(verdict)
log(f"VERDICT: {status}")
log(f"written -> {out}")
print("\n" + verdict)
