#!/usr/bin/env python3
"""THE LOCK: profile-log-lik over n on the two KNOWN-TRUTH synthetic regimes, SAME measure as the
real-data profile (profile_ll_ridge.py) — apples-to-apples (the recovery control used ll-across-shapes,
a different measure, so it could not calibrate the real profile).

n_true = 0.5 in BOTH. Decisive readout:
  REGIME A (separated timescales): expect profile peaks SHARPLY at n≈0.5 -> the estimator's profile
           correctly locates a sub-critical truth.
  REGIME B (overlapping, matched to markets): the KEY test. If B's profile FALSELY peaks at high n
           (≫0.5) despite n_true=0.5, then a steep-profile-peaking-high is a DEGENERACY ARTIFACT, and
           the real markets' near-critical profile peak (0.75–0.90) is that SAME artifact -> n
           NON-IDENTIFIED / over-estimated. If B correctly peaks near 0.5, a steep profile = genuine
           identification, and the real near-critical peak is REAL (Hardiman–Bouchaud, identified).
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
N_TRUE = 0.5
REGIMES = [("A short-mem+mild ramp (separated -> expect peak~0.5)", 1.6, 0.5, 2.0, 0.9, 6000.0),
           ("B long-mem+strong ramp (overlap, matched -> KEY)", 0.3, 0.5, 8.0, 0.30, 6000.0)]


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


lines = [f"# Profile-ll calibration on known-truth synthetics (n_true={N_TRUE}) — {time.strftime('%Y-%m-%d %H:%M:%S')}",
         "Same profile-over-n measure as the real-data ridge. Does a known-non-identified regime falsely peak high?", ""]
for label, eps_t, c_t, ramp, mu0, T in REGIMES:
    t = simulate_ramp(mu0, ramp, N_TRUE, T, eps_t, c_t, np.random.default_rng(11))
    N = t.size
    log(f"[{label}] N={N}")
    prof = []
    for n in N_GRID:
        cells = [(eps, c, fit_mu_only(t, T, PowerLawKernel(eps=eps, c=c), n, K_FLEX)["ll"])
                 for eps in EPS_GRID for c in C_GRID]
        eps_b, c_b, ll_b = max(cells, key=lambda x: x[2])
        prof.append((n, ll_b, eps_b, c_b))
        log(f"   n={n:.2f} profile_ll={ll_b:.0f} argmax(eps={eps_b},c={c_b})")
    llmax = max(p[1] for p in prof)
    pk = max(prof, key=lambda p: p[1])
    lines += [f"## {label}  (true eps={eps_t}, c={c_t}, ramp={ramp}x, n_true={N_TRUE}; N={N})",
              f"{'n':>5} {'Δprofile_ll':>13} {'argmax eps':>11} {'c':>5}"]
    for n, ll, eps_b, c_b in prof:
        lines.append(f"{n:>5.2f} {ll - llmax:>13.1f} {eps_b:>11} {c_b:>5}")
    lines += [f"- profile PEAK at n={pk[0]:.2f} (true {N_TRUE}); argmax eps={pk[2]}",
              f"- => {'peak near truth -> profile LOCATES n correctly' if abs(pk[0]-N_TRUE)<0.2 else 'peak FAR from truth (n=%.2f vs 0.5) -> profile MIS-locates -> steep-high-peak is a DEGENERACY ARTIFACT' % pk[0]}",
              ""]
outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_synth_profile_calibration.md"
outp.write_text("\n".join(lines))
log(f"-> {outp}")
print("\n" + "\n".join(lines))
