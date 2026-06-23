#!/usr/bin/env python3
"""Grid-extension check: does the profile peak STAY PUT or MIGRATE as the (eps) grid is opened toward
the heavy-tail boundary? The interior maxima (…9630 n=0.75, …9076 n=0.90) sit at boundary shapes
(eps=0.1, c=2.0); opening eps smaller raises ll toward the heavier tail, and the question is where the
PEAK-n lands:
  peak-n STAYS PUT as eps_min shrinks -> real interior maximum -> identification HOLDS.
  peak-n CLIMBS toward 1 (and beyond) as eps_min shrinks -> the interior peak was a truncation artifact,
    the steepness is the boundary wall not information -> degeneracy / non-identification.
One pass over a wide grid; peak-n is then read at successive eps_min cutoffs. n extended to 1.2 to catch
a peak running past criticality (n>1 evaluated as a fixed likelihood argument, not simulated).
"""
import pathlib
import sys
import time

SPIKE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPIKE))
import numpy as np
from b_reader import read_markets
from critaudit.hawkes.binned import PowerLawKernel
from mu_t_hawkes import fit_mu_only

OUT = "/Users/zenith/b_capture/ws_capture.jsonl"
RESULTS = SPIKE.parent.parent / "results" / "s0.4_feasibility"
FLOOR, SLEEP_GAP_S, K_FLEX = 16000, 60.0, 12
N_GRID = [0.30, 0.45, 0.60, 0.75, 0.90, 1.05, 1.20]
EPS_FULL = [0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.1]       # extended toward heavy tail
C_GRID = [0.5, 1.0, 2.0]
EPS_MINS = [0.4, 0.2, 0.1, 0.05, 0.02]                 # successive grid-opening cutoffs


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


mk = read_markets(OUT, sleep_gap_s=SLEEP_GAP_S)
over = sorted((m for m in mk if m.n_events >= FLOOR), key=lambda m: m.n_events)
log(f"{len(over)} markets; wide-grid peak-migration, eps down to 0.02, n up to 1.2")

lines = [f"# Grid-extension peak migration — {time.strftime('%Y-%m-%d %H:%M:%S')}",
         "peak-n vs eps_min cutoff. STAYS PUT = interior max (identified); CLIMBS toward 1 = runaway.", ""]
for m in over:
    T, N = m.horizon, m.n_events
    # ll[(n,eps,c)] over the full grid
    ll = {}
    for n in N_GRID:
        for eps in EPS_FULL:
            for c in C_GRID:
                ll[(n, eps, c)] = fit_mu_only(m.times, T, PowerLawKernel(eps=eps, c=c), n, K_FLEX)["ll"]
        log(f"...{m.asset_id[-10:]} n={n:.2f} done")
    lines += [f"## ...{m.asset_id[-10:]}  (N={N}, horizon={T/3600:.1f}h)",
              f"{'eps_min':>8} {'peak-n':>7} {'argmax eps':>11} {'argmax c':>9}"]
    peaks = []
    for emin in EPS_MINS:
        epss = [e for e in EPS_FULL if e >= emin]
        prof = [(n, max((ll[(n, e, c)], e, c) for e in epss for c in C_GRID)) for n in N_GRID]
        pk_n, (pk_ll, pk_e, pk_c) = max(prof, key=lambda x: x[1][0])
        peaks.append(pk_n)
        lines.append(f"{emin:>8} {pk_n:>7.2f} {pk_e:>11} {pk_c:>9}")
    migrated = peaks[-1] - peaks[0]
    lines += [f"- peak-n: {peaks[0]:.2f} (eps_min=0.4) -> {peaks[-1]:.2f} (eps_min=0.02); Δ={migrated:+.2f}",
              f"- => {'STAYS PUT -> real interior maximum, identification HOLDS' if abs(migrated) < 0.15 and peaks[-1] < 1.0 else 'CLIMBS toward/past 1 -> truncation artifact, runaway/degeneracy'}",
              ""]
outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_grid_extension_peak.md"
outp.write_text("\n".join(lines))
log(f"-> {outp}")
print("\n" + "\n".join(lines))
