#!/usr/bin/env python3
"""The rigorous likelihood ridge (replaces the KS-stat proxy). PROFILE log-likelihood over n:
profile_ll(n) = max over the (eps,c) shape grid of fit_mu_only(... n fixed ...).ll, with a flexible
linear μ(t). Two-part readout (per the lock spec):
  (1) SHALLOW: if profile_ll varies < ~2 units across n from sub-critical to ~1, the likelihood interval
      on n spans the whole range -> n NON-IDENTIFIED (the real claim, on the likelihood not a proxy).
  (2) RISING/RUNAWAY: if profile keeps rising toward n->1+ with the argmax shape running to eps->0
      (heavy tail) and no interior maximum -> DEGENERACY (kernel and baseline mutually substitutable as
      memory grows). The super-critical corner is the degeneracy signature, NOT physical criticality
      (a super-critical Hawkes has no stationary distribution; the value is a finite-window artifact).
eps bracketed down to 0.1 to confirm the runaway is not a grid-edge artifact.
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
N_GRID = [0.15, 0.30, 0.45, 0.60, 0.75, 0.90, 1.05]
EPS_GRID = [0.1, 0.2, 0.4, 0.7, 1.1]                    # bracketed down to 0.1
C_GRID = [0.5, 1.0, 2.0]


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


mk = read_markets(OUT, sleep_gap_s=SLEEP_GAP_S)
over = sorted((m for m in mk if m.n_events >= FLOOR), key=lambda m: m.n_events)
log(f"{len(over)} markets; profile ll over n={N_GRID}, shape eps={EPS_GRID} x c={C_GRID}")

lines = [f"# Profile log-likelihood ridge over n — {time.strftime('%Y-%m-%d %H:%M:%S')}",
         "profile_ll(n) = max over (eps,c) of the n-fixed flexible-μ(t) fit. Shallow across n = "
         "non-identified; rising-to-boundary with argmax eps->0.1 = degeneracy runaway.", ""]
for m in over:
    T, N = m.horizon, m.n_events
    prof = []
    for n in N_GRID:
        cells = [(eps, c, fit_mu_only(m.times, T, PowerLawKernel(eps=eps, c=c), n, K_FLEX)["ll"])
                 for eps in EPS_GRID for c in C_GRID]
        eps_b, c_b, ll_b = max(cells, key=lambda x: x[2])
        prof.append((n, ll_b, eps_b, c_b))
        log(f"...{m.asset_id[-10:]} n={n:.2f}  profile_ll={ll_b:.0f}  argmax(eps={eps_b},c={c_b})")
    llmax = max(p[1] for p in prof)
    lines += [f"## ...{m.asset_id[-10:]}  (N={N}, horizon={T/3600:.1f}h)",
              f"{'n':>5} {'Δprofile_ll':>13} {'argmax eps':>11} {'c':>5}"]
    for n, ll, eps_b, c_b in prof:
        lines.append(f"{n:>5.2f} {ll - llmax:>13.1f} {eps_b:>11} {c_b:>5}")
    # shallow across sub-critical [0.30,0.90]?
    sub = [p[1] for p in prof if 0.30 <= p[0] <= 0.90]
    span = max(sub) - min(sub)
    argmax_n = max(prof, key=lambda p: p[1])
    lines += [f"- profile_ll span across n∈[0.30,0.90] = {span:.1f} units "
              f"({'SHALLOW <2 -> n NON-IDENTIFIED' if span < 2 else 'has curvature -> some n info'})",
              f"- profile max at n={argmax_n[0]:.2f}, eps={argmax_n[2]} "
              f"({'BOUNDARY/runaway -> degeneracy, no interior sub-critical max' if argmax_n[0] >= 1.0 or argmax_n[2] <= 0.1 else 'interior'})",
              ""]
outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_profile_ll_ridge.md"
outp.write_text("\n".join(lines))
log(f"-> {outp}")
print("\n" + "\n".join(lines))
