#!/usr/bin/env python3
"""Joint-fit RECOVERY CONTROL — the control the joint fit lacked. The μ(t) sweep was licensed by the
synthetic ramp-recovery of the FIXED-shape estimator; the joint fit is a NEW 4-freedom estimator
(eps, c, μ(t), n) and weak identification is the DEFAULT when you free four things — so a real-data
ridge does not by itself prove the DATA is non-identified vs the ESTIMATOR being generically soft.

Known-truth synthetic through the SAME joint (eps,c)-grid x flexible linear μ(t), TWO regimes that vary
the kernel-memory vs ramp timescale OVERLAP:
  REGIME A  short memory (large eps) + mild ramp  -> timescales SEPARATE -> EXPECT recovery (n̂ pins at
            n_true, an interior max near the true shape, no runaway).
  REGIME B  long memory (small eps) + strong ramp (matched to the real markets) -> timescales COLLIDE
            -> EXPECT a ridge (n̂ spans widely, ML runs to the heavy-tail boundary, n̂ -> super-critical),
            reproducing the real-data behaviour ON KNOWN TRUTH.
If A recovers and B ridges, the timescale-overlap limit is reproduced on demand and the real-market
ridge is licensed as a property of the data, with the markets sitting in regime B.
"""
import pathlib
import sys
import time

SPIKE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPIKE))
import numpy as np
from scipy.stats import kstest
from critaudit.hawkes.binned import PowerLawKernel
from mu_t_hawkes import fit_mu_t_linear, rescaled_times_mu_t_linear

RESULTS = SPIKE.parent.parent / "results" / "s0.4_feasibility"
K_FLEX = 12
EPS_GRID = [0.2, 0.3, 0.5, 0.8, 1.2, 1.6]
C_GRID = [0.5, 1.0]
N_TRUE = 0.5
# (label, eps_true, c_true, ramp, mu0, T) -- mu0 tuned for ~1.5-2e4 events at n=0.5
REGIMES = [("A short-mem + mild ramp (separated)", 1.6, 0.5, 2.0, 0.9, 6000.0),
           ("B long-mem + strong ramp (overlap, matched)", 0.3, 0.5, 8.0, 0.30, 6000.0)]


def simulate_ramp(mu0, ramp, n, T, eps, c, rng):
    mu_max = mu0 * (1.0 + max(ramp, 0.0))
    cand = rng.uniform(0, T, rng.poisson(mu_max * T))
    imm = cand[rng.uniform(0, 1, cand.size) < (mu0 * (1.0 + ramp * cand / T)) / mu_max]
    times, queue = list(imm), list(imm)
    while queue:
        p = queue.pop()
        k = rng.poisson(n)
        if k:
            for ct in p + c * ((1.0 - rng.uniform(0, 1, k)) ** (-1.0 / eps) - 1.0):
                if ct < T:
                    times.append(ct); queue.append(ct)
    return np.sort(np.asarray(times, float))


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


lines = [f"# Joint-fit recovery control (two-regime, known truth n={N_TRUE}) — {time.strftime('%Y-%m-%d %H:%M:%S')}",
         f"Same joint (eps,c)-grid x flexible linear μ(t) K={K_FLEX} as the real-data joint fit.", ""]
for label, eps_t, c_t, ramp, mu0, T in REGIMES:
    t = simulate_ramp(mu0, ramp, N_TRUE, T, eps_t, c_t, np.random.default_rng(7))
    N = t.size
    d_good = 1.0 / np.sqrt(N)
    log(f"[{label}] true eps={eps_t} c={c_t} ramp={ramp} n={N_TRUE} -> N={N}")
    grid = []
    for eps in EPS_GRID:
        for c in C_GRID:
            r = fit_mu_t_linear(t, T, PowerLawKernel(eps=eps, c=c), K_FLEX)
            d = np.diff(rescaled_times_mu_t_linear(t, r["mus"], r["edges"], r["n"], eps, c))
            dks = float(kstest(d, "expon").statistic)
            grid.append((eps, c, r["n"], r["ll"], dks))
            log(f"   eps={eps} c={c}  n̂={r['n']:.3f}  D={dks:.4f}")
    best = max(grid, key=lambda g: g[3])              # max log-lik
    n_lo, n_hi = min(g[2] for g in grid), max(g[2] for g in grid)
    lines += [f"## {label}  (true eps={eps_t}, c={c_t}, ramp={ramp}x, n_true={N_TRUE}; N={N})  D_good≈{d_good:.4f}",
              f"{'eps':>5} {'c':>5} {'n̂':>7} {'ll':>11} {'D_KS':>8}"]
    for eps, c, nn, ll, dks in grid:
        mark = "  <-max-ll" if (eps, c) == (best[0], best[1]) else ""
        lines.append(f"{eps:>5} {c:>5} {nn:>7.3f} {ll:>11.0f} {dks:>8.4f}{mark}")
    recovered = abs(best[2] - N_TRUE) < 0.15 and best[0] >= 0.8
    lines += [f"- n̂ range across grid: {n_lo:.3f} .. {n_hi:.3f}   (true {N_TRUE})",
              f"- max-ll shape: eps={best[0]}, c={best[1]} -> n̂={best[2]:.3f}",
              f"- => {'RECOVERED (max-ll near true shape & n̂≈n_true, no runaway)' if recovered else 'RIDGE (n̂ spans / runs to heavy-tail boundary, no interior pin)'}",
              ""]
outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_joint_recovery_control.md"
outp.write_text("\n".join(lines))
log(f"-> {outp}")
print("\n" + "\n".join(lines))
