#!/usr/bin/env python3
"""Joint n↔eps↔μ(t) fit — STAGE 1: free the kernel SHAPE while the smooth μ(t) baseline is flexible.
The only test that clears the wrong-shape confound on "D never good". Reuses the validated
fit_mu_t_linear (no new estimator) — a grid over (eps, c), each fit with a flexible linear μ(t).

Readout: if the BEST (min-D) shape over the grid STILL has D >> good-fit (1/sqrt(N)) even with a
flexible smooth baseline -> no (shape, μ(t)) combo fits -> deep model problem / locked. If some shape
reaches ~good-fit D -> a fitting shape exists; its n̂ is the candidate, and STAGE 2 (sweep K at that
shape) tests whether n̂ is PINNED (identified, recoverable) or still slides (locked non-identification,
now surviving the correct shape = the genuine three-way ridge).
"""
import pathlib
import sys
import time

SPIKE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPIKE))
import numpy as np
from scipy.stats import kstest
from b_reader import read_markets
from critaudit.hawkes.binned import PowerLawKernel
from mu_t_hawkes import fit_mu_t_linear, rescaled_times_mu_t_linear

OUT = "/Users/zenith/b_capture/ws_capture.jsonl"
RESULTS = SPIKE.parent.parent / "results" / "s0.4_feasibility"
FLOOR, SLEEP_GAP_S, K_FLEX = 16000, 60.0, 12
EPS_GRID = [0.2, 0.4, 0.7, 1.1]
C_GRID = [0.5, 1.0, 2.0]


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def d_ks(t, r, eps, c):
    d = np.diff(rescaled_times_mu_t_linear(t, r["mus"], r["edges"], r["n"], eps, c))
    return float(kstest(d, "expon").statistic) if d.size > 1 else np.nan


mk = read_markets(OUT, sleep_gap_s=SLEEP_GAP_S)
over = sorted((m for m in mk if m.n_events >= FLOOR), key=lambda m: m.n_events)
log(f"{len(over)} over-floor markets; joint (eps,c)-grid x flexible linear μ(t) at K={K_FLEX}")

lines = [f"# Joint n↔eps↔μ(t) fit — stage 1 (best shape | flexible smooth μ(t)) — {time.strftime('%Y-%m-%d %H:%M:%S')}",
         f"Grid eps={EPS_GRID} x c={C_GRID}, linear μ(t) K={K_FLEX}.", ""]
for m in over:
    T, N = m.horizon, m.n_events
    d_good = 1.0 / np.sqrt(N)
    grid = []
    for eps in EPS_GRID:
        for c in C_GRID:
            r = fit_mu_t_linear(m.times, T, PowerLawKernel(eps=eps, c=c), K_FLEX)
            d = d_ks(m.times, r, eps, c)
            grid.append((eps, c, r["n"], d))
            log(f"...{m.asset_id[-10:]} eps={eps} c={c}  n̂={r['n']:.3f}  D={d:.4f}")
    best = min(grid, key=lambda g: g[3])
    lines += [f"## ...{m.asset_id[-10:]}  (N={N}, horizon={T/3600:.1f}h)  D_good≈{d_good:.4f}",
              f"{'eps':>5} {'c':>5} {'n̂':>7} {'D_KS':>8}"]
    for eps, c, nn, d in grid:
        mark = "  <-best" if (eps, c) == (best[0], best[1]) else ""
        lines.append(f"{eps:>5} {c:>5} {nn:>7.3f} {d:>8.4f}{mark}")
    ratio = best[3] / d_good
    lines += [f"- BEST shape: eps={best[0]}, c={best[1]} -> n̂={best[2]:.3f}, D={best[3]:.4f} "
              f"({ratio:.1f}x good-fit)",
              f"- {'GOOD FIT reachable -> a fitting (shape, μ(t)) EXISTS; STAGE 2: is n̂ pinned at this shape?' if ratio < 2 else 'NO shape reaches good-fit even with flexible smooth μ(t) -> leans LOCKED (deep model problem / genuine non-identification surviving free shape)'}",
              ""]
outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_joint_fit_stage1.md"
outp.write_text("\n".join(lines))
log(f"-> {outp}")
print("\n" + "\n".join(lines))
