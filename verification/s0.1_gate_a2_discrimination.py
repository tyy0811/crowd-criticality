"""S0.1 decision probe: Gate A.2 discriminating power at achievable N.

The keep-vs-demote question for the scaling-relation gate reduces to one measurement:
can A.2 separate a genuine SMALL scaling violation from a truly critical generator,
across seeds, at the event counts the project will actually have? This reports the
RESOLUTION  Delta_min(N) = 2*sqrt(2)*SD_seed(Delta_crit)  -- the smallest violation
distinguishable from critical across realizations -- and confirms known partial-shuffle
violations are caught when they exceed it. Multi-seed (8) is the load-bearing axis
(single-seed noise was what produced the phantom bias floor).

Finding: Delta_crit -> 0 with N (no bias floor), but Delta_min is coarse (~0.24 at 100k,
~0.12 at 400k) and is set by the CSN marginal-exponent seed-variance, not the 1/snz
estimator -- so the coarseness is intrinsic and not fixable by estimator choice.

Run: python verification/s0.1_gate_a2_discrimination.py
"""
from __future__ import annotations
import warnings
import numpy as np
import powerlaw

warnings.filterwarnings("ignore")


def gw(m, k, rng, cap=10**6):
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


def csn(x):
    return float(powerlaw.Fit(x, discrete=True, verbose=False).power_law.alpha)


def curv(s, d, mc=50):
    T, M = [], []
    for t in np.unique(d):
        if (d == t).sum() >= mc:
            T.append(t); M.append(s[d == t].mean())
    T = np.array(T, float); M = np.array(M)
    X = np.column_stack([np.ones_like(T), np.log(T), 1 / T])
    return float(np.linalg.lstsq(X, np.log(M), rcond=None)[0][1])


def pshuffle(d, f, rng):
    d = d.copy(); n = len(d); k = int(f * n)
    idx = rng.choice(n, k, replace=False); d[idx] = d[rng.permutation(idx)]
    return d


SEEDS = range(1, 9)
FRACS = [0.05, 0.10, 0.20, 0.40]

if __name__ == "__main__":
    print("=== Gate A.2 discriminating power: resolution Delta_min(N) vs known violations ===")
    for N in (20000, 50000, 100000, 200000, 400000):
        dcrit = []; Vf = {f: [] for f in FRACS}
        for sd in SEEDS:
            s, d = gw(1.0, N, np.random.default_rng(sd))
            ratio = (csn(d) - 1) / (csn(s) - 1); cc = curv(s, d)
            dcrit.append(ratio - cc)
            for f in FRACS:
                Vf[f].append(cc - curv(s, pshuffle(d, f, np.random.default_rng(1000 + sd))))
        sdd = np.std(dcrit, ddof=1); dmin = 2 * np.sqrt(2) * sdd
        print(f"N={N:6d}: Delta_crit={np.mean(dcrit):+.3f}  SD_seed={sdd:.3f}  ->  Delta_min={dmin:.3f}")
        for f in FRACS:
            v = np.mean(Vf[f])
            print(f"        violation f={f:.2f}: V={v:.3f}  {'RESOLVED' if v > dmin else 'below resolution'}")
