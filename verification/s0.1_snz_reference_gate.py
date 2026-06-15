"""S0.1 verify-then-lock, part 2: bias-floor diagnosis + reference-differenced Gate A.2.

Follows the estimator triangulation (s0.1_snz_estimator_triangulation.py). The triangulation
left a residual: even the best estimators give Delta != 0 on a genuinely critical generator.
This study resolves what that residual is and how the gate must respond.

Step 1 (bias_floor_check): push N past 100k. Does each estimator's 1/sigma-nu-z point
  converge to the known 2.0 (benign) or saturate below it (a genuine bias FLOOR)?
  Finding: curv slowly CONVERGES (1.865->1.929 over 100k->800k); tail FLOORS at ~1.874.

Step 2 (reference_gate_demo): a bias floor makes "consistent = Delta-CI contains 0" FAIL at
  large N — as the CI tightens below the bias it EXCLUDES 0 and a genuinely critical system
  reads "inconsistent" (a false rejection that worsens with data; the ceiling can't prevent
  it because "excludes 0" isn't ceiling-governed). Fix (the right null): score the test
  system's Delta against the SAME estimator's Delta on a matched synthetic-critical REFERENCE,
  not against 0. The common bias differences out -> critical stays consistent at all N;
  the look-alike's genuine violation survives the differencing -> still rejected.
  This is Gate-D-clean (calibrated on the synthetic critical generator, never on test n/Delta).

NOTE: Step 2 fixes x_min per generator for speed (the honest reselect-x_min CIs were
characterized at <=100k in the triangulation bootstrap). Fixed x_min understates CI width,
so it makes the OLD-gate flip appear even for curv; the reference gate rescues both anyway,
which is the robustness point.

Run: python verification/s0.1_snz_reference_gate.py
"""
from __future__ import annotations
import warnings
import numpy as np
import powerlaw

warnings.filterwarnings("ignore")


def gw(m, k, rng, cap=10**7):
    S = np.empty(k, np.int64); D = np.empty(k, np.int64); C = np.zeros(k, bool)
    for i in range(k):
        s = 0; cur = 1; g = 0; c = False
        while cur > 0:
            g += 1; s += cur
            if s > cap:
                c = True; break
            cur = int(rng.poisson(m * cur))
        S[i] = s; D[i] = g; C[i] = c
    return S[~C], D[~C]


def alpha(x, xmin=None):
    return float(powerlaw.Fit(x, discrete=True, xmin=xmin, verbose=False).power_law.alpha)


def xmin_of(x):
    return float(powerlaw.Fit(x, discrete=True, verbose=False).power_law.xmin)


def curv(s, d, mc=50):
    T, M = [], []
    for t in np.unique(d):
        if (d == t).sum() >= mc:
            T.append(t); M.append(s[d == t].mean())
    T = np.array(T, float); M = np.array(M)
    X = np.column_stack([np.ones_like(T), np.log(T), 1.0 / T])
    return float(np.linalg.lstsq(X, np.log(M), rcond=None)[0][1])


def tail(s, d, q=80):
    thr = np.percentile(d, q); m = d >= thr
    return float(np.polyfit(np.log(d[m]), np.log(s[m]), 1)[0])


def bias_floor_check(rng):
    print("=== Step 1: bias-floor check (point estimates, large N; target 1/snz -> 2.0) ===")
    print(f"{'N':>8} {'ratio':>6} {'curv':>6} {'tail':>6} | {'D_curv':>7} {'D_tail':>7}")
    for N in (100000, 200000, 400000, 800000):
        s, d = gw(1.0, N, rng)
        r = (alpha(d) - 1) / (alpha(s) - 1); cv = curv(s, d); tl = tail(s, d)
        print(f"{N:>8} {r:6.3f} {cv:6.3f} {tl:6.3f} | {r - cv:+7.3f} {r - tl:+7.3f}")
    print("  curv climbs toward 2 (slow convergence, benign); tail saturates ~1.874 (genuine floor).")


def _boot(s, d, B, rng):
    xs, xd = xmin_of(s), xmin_of(d); N = len(s)
    cd = np.empty(B); td = np.empty(B)
    for b in range(B):
        idx = rng.integers(0, N, N); ss, dd = s[idx], d[idx]
        r = (alpha(dd, xd) - 1) / (alpha(ss, xs) - 1)
        cd[b] = r - curv(ss, dd); td[b] = r - tail(ss, dd)
    return cd, td


def reference_gate_demo(N=250000, B=25):
    print(f"\n=== Step 2: reference-differenced gate @ N={N}, B={B} (fixed x_min) ===")
    sA, dA = gw(1.0, N, np.random.default_rng(101))                 # critical reference
    sB, dB = gw(1.0, N, np.random.default_rng(202))                 # critical test (independent)
    perm = np.random.default_rng(303).permutation(len(sA))
    sLA, dLA = sA[perm], dA                                         # look-alike (S-T shuffle)
    rng = np.random.default_rng(404)
    rc, rt = _boot(sA, dA, B, rng); bc, bt = _boot(sB, dB, B, rng); lc, lt = _boot(sLA, dLA, B, rng)

    def ci(x):
        lo, hi = np.percentile(x, [2.5, 97.5]); return lo, hi
    for name, refd, bd, ld in (("curv", rc, bc, lc), ("tail", rt, bt, lt)):
        lo, hi = ci(bd)
        l2, h2 = ci(bd - refd)
        l3, h3 = ci(ld - refd)
        print(f"[{name}] OLD contains0 on CRITICAL test:  CI=({lo:+.3f},{hi:+.3f}) -> {lo <= 0 <= hi}")
        print(f"       REF crit-vs-ref:      d-CI=({l2:+.3f},{h2:+.3f}) -> consistent={l2 <= 0 <= h2}")
        print(f"       REF lookalike-vs-ref: d-CI=({l3:+.3f},{h3:+.3f}) -> rejected={not (l3 <= 0 <= h3)}")


if __name__ == "__main__":
    bias_floor_check(np.random.default_rng(21))
    reference_gate_demo()
