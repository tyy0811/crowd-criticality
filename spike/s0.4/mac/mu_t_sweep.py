#!/usr/bin/env python3
"""The DECISIVE sweep: piecewise-constant μ(t) flexibility K vs n̂, on the over-floor markets.

For each market, sweep K (equal-event-count baseline segments) and record n̂(K), AIC/BIC(K), and the
cheap μ(t)-rescaled KS statistic D(K) (no bootstrap). READOUT (not n̂ movement — n̂ falling is expected):
the IDENTIFIED signal is a PLATEAU where added flexibility stops lowering n̂, with the IC-selected K
(min BIC) landing IN it. The plateau value is the trustworthy n̂. Monotonic descent / IC-K on the slope
= non-identified (endo/exo inseparable). D(K): if it drops to ~good-fit (~1/sqrt(N)) as μ(t) flexes,
μ(t) was the problem and the shape rejection dissolves; if D stays high at every K, shape is live
underneath = the n↔eps↔μ(t) entanglement branch.

Method validated on synthetic ground truth (test_mu_t_hawkes: K=1 inflates, plateau recovers true
sub-critical n under a known ramp).
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
from mu_t_hawkes import fit_mu_t, rescaled_times_mu_t

OUT = "/Users/zenith/b_capture/ws_capture.jsonl"
RESULTS = SPIKE.parent.parent / "results" / "s0.4_feasibility"
EPS, C, FLOOR, SLEEP_GAP_S = 0.4, 0.5, 16000, 60.0
KS = [1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32]
k = PowerLawKernel(eps=EPS, c=C)


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def d_ks(t, r):
    d = np.diff(rescaled_times_mu_t(t, r["mus"], r["edges"], r["n"], EPS, C))
    return float(kstest(d, "expon").statistic) if d.size > 1 else np.nan


mk = read_markets(OUT, sleep_gap_s=SLEEP_GAP_S)
over = sorted((m for m in mk if m.n_events >= FLOOR), key=lambda m: m.n_events)
log(f"{len(over)} over-floor markets; sweeping K={KS}")

lines = [f"# Piecewise-μ(t) flexibility sweep — n̂(K) vs K — {time.strftime('%Y-%m-%d %H:%M:%S')}", "",
         "Readout: plateau (added K stops lowering n̂) + IC-K (min BIC) IN the plateau + GoF ok there =",
         "identified, plateau value = trustworthy n̂. Monotonic descent / IC-K on slope = non-identified.",
         f"D_good ≈ 1/sqrt(N) is the target KS for a good fit.", ""]
for m in over:
    T, N = m.horizon, m.n_events
    fits = {}
    for K in KS:
        r = fit_mu_t(m.times, T, k, K)
        r["d"] = d_ks(m.times, r)
        fits[K] = r
        log(f"...{m.asset_id[-10:]} K={K:2d}  n̂={r['n']:.3f}  D={r['d']:.4f}  BIC={r['bic']:.0f}")
    bic_K = min(KS, key=lambda K: fits[K]["bic"])
    aic_K = min(KS, key=lambda K: fits[K]["aic"])
    d_good = 1.0 / np.sqrt(N)
    lines += [f"## ...{m.asset_id[-10:]}  (N={N}, horizon={T/3600:.1f}h)  D_good≈{d_good:.4f}",
              f"{'K':>4} {'n̂':>7} {'D_KS':>8} {'AIC':>12} {'BIC':>12}"]
    for K in KS:
        r = fits[K]
        mark = "  <-BIC*" if K == bic_K else ("  <-AIC*" if K == aic_K else "")
        lines.append(f"{K:>4} {r['n']:>7.3f} {r['d']:>8.4f} {r['aic']:>12.0f} {r['bic']:>12.0f}{mark}")
    # plateau heuristic: successive |Δn̂|<0.03
    ns = [fits[K]["n"] for K in KS]
    dn = [abs(ns[i] - ns[i - 1]) for i in range(1, len(KS))]
    plateau_start = next((KS[i] for i in range(len(dn)) if dn[i] < 0.03), None)
    lines += [f"- BIC-selected K={bic_K} (n̂={fits[bic_K]['n']:.3f}, D={fits[bic_K]['d']:.4f}); "
              f"AIC-selected K={aic_K} (n̂={fits[aic_K]['n']:.3f})",
              f"- n̂: K=1 {ns[0]:.3f} -> K={KS[-1]} {ns[-1]:.3f}; plateau (|Δn̂|<0.03) starts ~K={plateau_start}",
              f"- BIC-K {'IN' if plateau_start and bic_K >= plateau_start else 'NOT in'} plateau; "
              f"D at BIC-K {'≈good' if fits[bic_K]['d'] < 2 * d_good else 'still high (entanglement?)'}",
              ""]
outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_mu_t_sweep.md"
outp.write_text("\n".join(lines))
log(f"-> {outp}")
print("\n" + "\n".join(lines))
