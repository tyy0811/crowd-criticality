#!/usr/bin/env python3
"""Non-stationarity check — does the 0/3 GoF rejection (and the n̂≈0.8 values) reflect KERNEL SHAPE, or
a non-stationary rate that a STATIONARY Hawkes absorbs into n̂ (Hawkes-vs-inhomogeneous-Poisson)?

Two complementary, cheap, model-light signals per over-floor market (gap-guarded), NO new machinery:

 (A) DIRECT rate trajectory: events/hour across K equal-time windows. Model-free, no edge effect. A
     large swing = non-stationarity is PRESENT.
 (B) n̂ INFLATION test: fit_full n̂ on whole vs halves vs thirds. If whole >> sub-windows, a stationary
     Hawkes is absorbing rate variation into n̂. Calibrated against a STATIONARY synthetic control
     (simulate at the fitted params; the same whole-vs-thirds gap under KNOWN stationarity is the pure
     edge effect from ignoring pre-window excitation). Real gap >> synthetic gap = genuine inflation.

Decisive readout: rate roughly flat AND real gap ~ synthetic gap -> stationary, the rejection is about
SHAPE, the fitter is the right next step. Rate swings AND real gap >> synthetic -> non-stationary, n̂ is
inflated, the shape-fitter is the WRONG tool (fix = inhomogeneous mu(t) / windowed fits), and "does n̂
measure reflexivity at all" reopens.
"""
import pathlib
import sys
import time

SPIKE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPIKE))
import numpy as np
from b_reader import read_markets
from critaudit.hawkes.binned import PowerLawKernel, fit_full
from critaudit.generators import powerlaw_hawkes

OUT = "/Users/zenith/b_capture/ws_capture.jsonl"
RESULTS = SPIKE.parent.parent / "results" / "s0.4_feasibility"
EPS, C, FLOOR, SLEEP_GAP_S = 0.4, 0.5, 16000, 60.0
K_RATE = 8            # rate-trajectory windows
SYNTH_SEEDS = 3       # stationary-control replicates
k = PowerLawKernel(eps=EPS, c=C)


def fit_window(times, lo, hi):
    """fit_full n̂ on events in [lo,hi), re-zero-based on their own span (the reader's convention)."""
    w = times[(times >= lo) & (times < hi)]
    if w.size < 50:
        return np.nan, np.nan, w.size
    w = w - w[0]
    mu, n = fit_full(w, float(w[-1]), k)
    return mu, n, w.size


def subwindow_gap(times, horizon):
    """whole n̂ minus the mean of thirds n̂ (the inflation signature, modulo edge effect)."""
    _, n_whole, _ = fit_window(times, 0.0, horizon + 1)
    thirds = [fit_window(times, j * horizon / 3, (j + 1) * horizon / 3)[1] for j in range(3)]
    thirds = [x for x in thirds if np.isfinite(x)]
    return n_whole, (np.mean(thirds) if thirds else np.nan), thirds


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


mk = read_markets(OUT, sleep_gap_s=SLEEP_GAP_S)
over = sorted((m for m in mk if m.n_events >= FLOOR), key=lambda m: m.n_events)
log(f"{len(over)} over-floor markets")

blocks = []
for m in over:
    T = m.horizon
    # (A) direct rate trajectory
    edges = np.linspace(0, T, K_RATE + 1)
    counts = np.histogram(m.times, bins=edges)[0]
    rates = counts / (T / K_RATE / 3600.0)               # events/hour per window
    swing = rates.max() / max(rates.min(), 1e-9)
    # (B) real sub-window inflation
    n_whole, n_thirds_mean, thirds = subwindow_gap(m.times, T)
    halves = [fit_window(m.times, 0.0, T / 2)[1], fit_window(m.times, T / 2, T + 1)[1]]
    real_gap = n_whole - n_thirds_mean
    # (B-control) stationary synthetic at the fitted params
    mu_w, _, _ = fit_window(m.times, 0.0, T + 1)
    syn_gaps = []
    for s in range(SYNTH_SEEDS):
        ts = powerlaw_hawkes.simulate(n_whole, T, mu_w, EPS, C, np.random.default_rng(1000 + s))
        if ts.size > 200:
            nw, nt, _ = subwindow_gap(ts, float(ts[-1]))
            if np.isfinite(nw) and np.isfinite(nt):
                syn_gaps.append(nw - nt)
    syn_gap = float(np.mean(syn_gaps)) if syn_gaps else np.nan
    log(f"...{m.asset_id[-10:]}  swing={swing:.1f}x  n_whole={n_whole:.3f}  "
        f"thirds={[round(x,2) for x in thirds]}  real_gap={real_gap:+.3f}  syn_gap={syn_gap:+.3f}")
    blocks.append((m.asset_id[-10:], m.n_events, T, rates, swing, n_whole, halves, thirds,
                   n_thirds_mean, real_gap, syn_gap, mu_w))

# writedown
lines = [f"# Non-stationarity check (over-floor markets) -- {time.strftime('%Y-%m-%d %H:%M:%S')}", "",
         f"Assumed shape eps={EPS}, c={C}; gap-guarded; K_RATE={K_RATE}; synthetic seeds={SYNTH_SEEDS}.",
         "n_whole = fit_full n on full history; thirds = n on each 1/3; real_gap = n_whole - mean(thirds);",
         "syn_gap = same gap on a STATIONARY simulate() at the fitted params (the pure edge effect).", ""]
for tail, N, T, rates, swing, nw, halves, thirds, ntm, rg, sg, muw in blocks:
    inflated = np.isfinite(sg) and (rg - sg) > 0.08
    lines += [f"## ...{tail}  (N={N}, horizon={T/3600:.1f}h, mu_full={muw:.3f})",
              f"- rate/hr per {K_RATE}-window: {[int(r) for r in rates]}",
              f"- rate SWING (max/min): {swing:.1f}x",
              f"- n_whole={nw:.3f}  halves={[round(x,3) for x in halves]}  thirds={[round(x,3) for x in thirds]}",
              f"- real_gap (whole - mean thirds) = {rg:+.3f}   synthetic stationary edge-effect gap = {sg:+.3f}",
              f"- => excess over edge effect = {rg - sg:+.3f}  {'<<< INFLATION (non-stationary)' if inflated else '(within edge effect -> consistent with stationary)'}",
              ""]
any_inflated = any((np.isfinite(b[10]) and (b[9] - b[10]) > 0.08) for b in blocks)
any_swing = any(b[4] > 5 for b in blocks)
lines += ["## Readout",
          f"- rate non-stationarity present (any swing >5x): {any_swing}",
          f"- n̂ inflation beyond edge effect (any excess >0.08): {any_inflated}",
          "",
          "- BOTH false -> stationary; the 0/3 rejection is about SHAPE; the (eps,c) fitter is the right",
          "  next step; take the design doc to cross-review.",
          "- EITHER true -> non-stationary; n̂ absorbs rate variation; the shape-fitter is the WRONG tool;",
          "  fix = inhomogeneous mu(t)/windowed fits; reopen whether n̂ measures reflexivity at all.",
          "- Either way: add non-stationarity to the fitter doc as a TESTED alternative (numbers in hand)."]
outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_nonstationarity_check.md"
outp.write_text("\n".join(lines))
log(f"swing_any={any_swing}  inflation_any={any_inflated} -> {outp}")
print("\n" + "\n".join(lines))
