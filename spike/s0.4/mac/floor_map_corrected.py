#!/usr/bin/env python3
"""CORRECTED floor map — the gating re-run before cross-review. Fixes the review findings that biased
the original maps toward the misspecification headline:

  #1 undershoot mislabel: OLD `recovered iff peak<=N_PLANT` counted a peak BELOW the plant (mis-located
     low) as identified. FIX: recovered iff |peak_n - N_PLANT| <= TOL (peak AT the plant — excludes BOTH
     undershoot and the supercritical runaway).
  #3 home-field bias: OLD test grid CONTAINED the planted shape, so the synthetic truth sat exactly on a
     grid node while a real market's true shape sits BETWEEN nodes — synthetic recovers more easily than
     real, the exact "synthetic recovers, real doesn't -> mis-modelled" inference. FIX: plant OFF-GRID
     (eps=0.35, c=1.7 — between test nodes) so synthetic and real stand on equal footing.
  #5 no error bar: OLD one fixed seed per cell. FIX: MC replication (SEEDS draws), report the recovered
     fraction; floor = smallest N where a majority recover.

Two-sided test of the headline: floor < 12k  -> markets 1,2 (18-22k) are ABOVE floor yet degenerate ->
MISSPECIFICATION stands. floor rises into 18-22k -> VOLUME-floor hypothesis returns -> headline flips to
identifiability-is-volume-gated (market 3 at 35k above it fits that too).
"""
import pathlib
import sys
import time

SPIKE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPIKE))
import numpy as np
from critaudit.hawkes.binned import PowerLawKernel
from mu_t_hawkes import fit_mu_only

RESULTS = SPIKE.parent.parent / "results" / "s0.4_feasibility"
K_FLEX = 12
N_PLANT, EPS_PLANT, C_PLANT, RAMP, T = 0.85, 0.35, 1.7, 10.0, 50000.0   # plant OFF the test grid
EPS_TEST, C_TEST = [0.2, 0.4, 0.8], [1.0, 2.0]                          # 0.35/1.7 sit BETWEEN nodes
N_GRID = [0.60, 0.75, 0.85, 0.95, 1.05, 1.20]
N_TARGETS = [10000, 14000, 18000, 24000, 32000]
SEEDS = 4
TOL = 0.10                                                             # recovered iff |peak-0.85|<=TOL


def simulate_ramp(mu0, ramp, n, T, eps, c, rng):
    mu_max = mu0 * (1.0 + max(ramp, 0.0))
    cand = rng.uniform(0, T, rng.poisson(mu_max * T))
    imm = cand[rng.uniform(0, 1, cand.size) < (mu0 * (1.0 + ramp * cand / T)) / mu_max]
    times, queue = list(imm), list(imm)
    while queue:
        p = queue.pop()
        kk = rng.poisson(n)
        if kk:
            for ct in p + c * ((1.0 - rng.uniform(0, 1, kk)) ** (-1.0 / eps) - 1.0):
                if ct < T:
                    times.append(ct); queue.append(ct)
    return np.sort(np.asarray(times, float))


def peak_n(t):
    prof = [(n, max(fit_mu_only(t, T, PowerLawKernel(eps=e, c=c), n, K_FLEX)["ll"]
                    for e in EPS_TEST for c in C_TEST)) for n in N_GRID]
    return max(prof, key=lambda x: x[1])[0]


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


log(f"corrected floor: plant n={N_PLANT} OFF-GRID eps={EPS_PLANT} c={C_PLANT}, ramp={RAMP}x, {SEEDS} seeds/cell")
rows = []
for Nt in N_TARGETS:
    mu0 = Nt * (1.0 - N_PLANT) / (T * (1.0 + RAMP / 2.0))
    peaks = []
    for s in range(SEEDS):
        t = simulate_ramp(mu0, RAMP, N_PLANT, T, EPS_PLANT, C_PLANT, np.random.default_rng(100 + s))
        pk = peak_n(t)
        peaks.append(pk)
        log(f"N_target={Nt:>6} seed={s} -> N={t.size:>6} peak-n={pk:.2f} "
            f"{'rec' if abs(pk - N_PLANT) <= TOL else ('under' if pk < N_PLANT else 'runaway')}")
    rec = sum(1 for pk in peaks if abs(pk - N_PLANT) <= TOL)
    rows.append((Nt, peaks, rec))

lines = [f"# CORRECTED floor map (off-grid plant, MC, fixed criterion) — {time.strftime('%Y-%m-%d %H:%M:%S')}",
         f"plant n={N_PLANT}, eps={EPS_PLANT}, c={C_PLANT} (OFF the test grid eps={EPS_TEST} x c={C_TEST}); "
         f"ramp={RAMP}x; recovered iff |peak-{N_PLANT}|<={TOL}; {SEEDS} seeds/cell.", "",
         f"{'N_target':>9} {'recovered':>10} {'peak-n per seed':>28}"]
for Nt, peaks, rec in rows:
    lines.append(f"{Nt:>9} {rec}/{SEEDS:>8} {str([round(p, 2) for p in peaks]):>28}")
floor = next((Nt for Nt, _, rec in rows if rec >= (SEEDS + 1) // 2 + (SEEDS % 2 == 0)), None)
maj = (SEEDS // 2) + 1
floor = next((Nt for Nt, _, rec in rows if rec >= maj), None)
lines += ["", f"## floor (smallest N with >= {maj}/{SEEDS} recovered): {floor if floor else '> %d' % N_TARGETS[-1]}",
          "",
          "Read: floor < 12k -> markets 1,2 (18-22k) are ABOVE floor yet degenerate -> MISSPECIFICATION",
          "stands (headline clean). floor in 18-22k -> VOLUME-floor hypothesis returns -> headline FLIPS to",
          "identifiability-is-volume-gated. This is the two-sided gate the cross-review rests on."]
outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_floor_map_corrected.md"
outp.write_text("\n".join(lines))
log(f"floor={floor} -> {outp}")
print("\n" + "\n".join(lines))
