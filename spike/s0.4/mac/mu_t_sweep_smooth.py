#!/usr/bin/env python3
"""Smooth-basis hardening: run the piecewise-LINEAR (continuous) μ(t) sweep SIDE-BY-SIDE with the
piecewise-constant one. Overturn power in both directions:
  - if n̂_linear PLATEAUS where n̂_const slid -> the step basis structurally hid a plateau (a linear piece
    absorbs within-piece trend the constant basis charged to n̂);
  - if D_linear reaches ~good-fit (1/sqrt(N)) at the IC-K WITH the fixed shape -> μ(t) was the whole
    problem and the 0/3 shape rejection DISSOLVES (it was the non-stationarity); if D_linear stays high
    -> entanglement confirmed, shape live underneath -> the joint n↔eps↔μ(t) fit is the decisive lock.
Both bases validated on synthetic ground truth (test_mu_t_hawkes).
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
from mu_t_hawkes import (fit_mu_t, rescaled_times_mu_t, fit_mu_t_linear, rescaled_times_mu_t_linear)

OUT = "/Users/zenith/b_capture/ws_capture.jsonl"
RESULTS = SPIKE.parent.parent / "results" / "s0.4_feasibility"
EPS, C, FLOOR, SLEEP_GAP_S = 0.4, 0.5, 16000, 60.0
KS = [1, 2, 4, 6, 8, 12, 16, 24, 32]
k = PowerLawKernel(eps=EPS, c=C)


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def d_of(t, r, resc):
    d = np.diff(resc(t, r["mus"], r["edges"], r["n"], EPS, C))
    return float(kstest(d, "expon").statistic) if d.size > 1 else np.nan


mk = read_markets(OUT, sleep_gap_s=SLEEP_GAP_S)
over = sorted((m for m in mk if m.n_events >= FLOOR), key=lambda m: m.n_events)
log(f"{len(over)} over-floor markets; constant vs linear μ(t), K={KS}")

lines = [f"# Smooth (piecewise-linear) vs step (piecewise-constant) μ(t) sweep — {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
for m in over:
    T, N = m.horizon, m.n_events
    d_good = 1.0 / np.sqrt(N)
    rows = []
    for K in KS:
        rc = fit_mu_t(m.times, T, k, K); rc["d"] = d_of(m.times, rc, rescaled_times_mu_t)
        rl = fit_mu_t_linear(m.times, T, k, K); rl["d"] = d_of(m.times, rl, rescaled_times_mu_t_linear)
        rows.append((K, rc["n"], rc["d"], rc["bic"], rl["n"], rl["d"], rl["bic"]))
        log(f"...{m.asset_id[-10:]} K={K:2d}  const n̂={rc['n']:.3f} D={rc['d']:.4f} | "
            f"linear n̂={rl['n']:.3f} D={rl['d']:.4f}")
    bicK_l = min(rows, key=lambda r: r[6])
    lines += [f"## ...{m.asset_id[-10:]}  (N={N}, horizon={T/3600:.1f}h)  D_good≈{d_good:.4f}",
              f"{'K':>4} | {'n̂_const':>8} {'D_const':>8} | {'n̂_lin':>7} {'D_lin':>7}"]
    for K, nc, dc, bc, nl, dl, bl in rows:
        mark = "  <-BIC_lin*" if (K, nl) == (bicK_l[0], bicK_l[4]) else ""
        lines.append(f"{K:>4} | {nc:>8.3f} {dc:>8.4f} | {nl:>7.3f} {dl:>7.4f}{mark}")
    nls = [r[4] for r in rows]
    lines += [f"- linear n̂: K=1 {nls[0]:.3f} -> K={KS[-1]} {nls[-1]:.3f}; BIC_lin-K={bicK_l[0]} "
              f"(n̂={bicK_l[4]:.3f}, D={bicK_l[5]:.4f})",
              f"- D_lin at BIC-K {'≈GOOD -> μ(t) may be the whole problem, shape rejection dissolves' if bicK_l[5] < 2*d_good else 'STILL HIGH -> entanglement, shape live underneath'}",
              ""]
outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_mu_t_sweep_smooth.md"
outp.write_text("\n".join(lines))
log(f"-> {outp}")
print("\n" + "\n".join(lines))
