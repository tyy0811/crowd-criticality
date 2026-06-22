#!/usr/bin/env python3
"""THE BREAK TEST (two-sided): matched recovery control. Plant EACH MARKET'S OWN fitted (eps, c, n) +
ramp + event-count + horizon, simulate, run the SAME profile-over-n, and ask whether it RECOVERS the
planted n. Read RECOVERY and PROFILE SHAPE (interior peak / flat / monotonic-rising), NOT raw ll-span
(span scales with event count -> confounded; that was the flaw in the eps=0.3 regime-B comparison).

  recovers (steep interior peak at the planted n) -> the real markets' steep interior peaks are real,
                                                     identification HOLDS, near-criticality genuine.
  fails (flat / mis-located / monotonic-rising)   -> this regime is non-identifiable even at KNOWN
                                                     truth -> the real steepness is an artifact ->
                                                     identification BROKEN. This failure mode is live.

Planted from each market's profile-ll argmax (results/2026-06-22_profile_ll_ridge.md) + its measured
rate-swing ramp (2026-06-21_nonstationarity_check.md). Market …3503 (peak n=1.05>1, supercritical) is
NOT simulable stationarily -> excluded here, flagged as the boundary/runaway case.
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
N_GRID = [0.15, 0.30, 0.45, 0.60, 0.75, 0.90, 1.05]
EPS_GRID = [0.1, 0.2, 0.4, 0.7, 1.1]
C_GRID = [0.5, 1.0, 2.0]
# (label, eps, c, n_plant, ramp, T, mu0)  -- mu0 tuned for the market's event count
MARKETS = [("…9630680686 (plant n=0.75)", 0.4, 2.0, 0.75, 9.5, 72000.0, 0.0133),
           ("…9076918150 (plant n=0.90)", 0.4, 2.0, 0.90, 11.7, 44280.0, 0.0115)]


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


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


lines = [f"# Matched recovery control — plant each market's own fit, recover the planted n? — {time.strftime('%Y-%m-%d %H:%M:%S')}",
         "Read RECOVERY + profile SHAPE, not raw span (span scales with N). Event count + ramp matched.", ""]
for label, eps_t, c_t, n_plant, ramp, T, mu0 in MARKETS:
    t = simulate_ramp(mu0, ramp, n_plant, T, eps_t, c_t, np.random.default_rng(21))
    N = t.size
    log(f"[{label}] planted eps={eps_t} c={c_t} n={n_plant} ramp={ramp}x -> N={N}")
    prof = []
    for n in N_GRID:
        cells = [(eps, c, fit_mu_only(t, T, PowerLawKernel(eps=eps, c=c), n, K_FLEX)["ll"])
                 for eps in EPS_GRID for c in C_GRID]
        eps_b, c_b, ll_b = max(cells, key=lambda x: x[2])
        prof.append((n, ll_b, eps_b, c_b))
        log(f"   n={n:.2f} profile_ll={ll_b:.0f} argmax(eps={eps_b},c={c_b})")
    llmax = max(p[1] for p in prof)
    pk = max(prof, key=lambda p: p[1])
    # shape: interior peak (max not at an n-grid end) vs monotonic-rising (max at top) vs flat
    span = llmax - min(p[1] for p in prof)
    shape = ("flat (span<10 -> non-identified)" if span < 10
             else "monotonic-rising to n-boundary (degeneracy)" if pk[0] == N_GRID[-1]
             else "interior peak")
    lines += [f"## {label}  (planted N={N}, ramp={ramp}x, n_true={n_plant})",
              f"{'n':>5} {'Δprofile_ll':>13} {'argmax eps':>11} {'c':>5}"]
    for n, ll, eps_b, c_b in prof:
        mk = "  <-peak" if (n, ll) == (pk[0], pk[1]) else ""
        lines.append(f"{n:>5.2f} {ll - llmax:>13.1f} {eps_b:>11} {c_b:>5}{mk}")
    recovered = abs(pk[0] - n_plant) <= 0.15 and shape == "interior peak"
    lines += [f"- profile PEAK at n={pk[0]:.2f} (planted {n_plant}); shape: {shape}; span {span:.0f} units",
              f"- => {'RECOVERED planted n -> real interior peaks are REAL, identification HOLDS' if recovered else 'FAILED to recover own known n -> regime non-identifiable at known truth -> real steepness is an ARTIFACT, identification BROKEN'}",
              ""]
outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_matched_recovery.md"
outp.write_text("\n".join(lines))
log(f"-> {outp}")
print("\n" + "\n".join(lines))
