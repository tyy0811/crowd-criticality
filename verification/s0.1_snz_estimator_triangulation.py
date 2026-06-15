"""S0.1 verify-then-lock study: 1/σνz estimator triangulation (Gate-A.2 blocker).

The naive binned-mean ⟨S|T⟩ slope false-negatives a genuinely critical generator
(DECISIONS.md 2026-06-15). Per the estimator-triangulation norm (plan §2.5), this
runs a set of 1/σνz estimators *chosen to fail differently* through identical gates
on Galton–Watson ground truth, selecting the lowest-DOF passer by a pre-committed,
result-blind criterion: point estimate → known value 2 AND CI tightening, look-alike
rejection, and mutual agreement (divergence is a finding).

Estimators (different data regions = independent anchors):
  - collapse : avalanche shape-collapse on the full per-avalanche profile (Friedman 2012)
  - tail     : OLS of log S on log T over the large-T tail (T ≥ 80th pct) — extreme region
  - curv     : curvature-corrected binned fit  log⟨S|T⟩ = a + γ logT + b/T  — bulk + modeled
  - binned   : naive binned-mean slope (the known-bad baseline)

This is a self-contained study; it does NOT import the (unbuilt) package. Its result
is the input to the Claude/ChatGPT cross-review before any estimator is locked into
the scaling module, spec §4.4, or the pre-registration.

Run: python verification/s0.1_snz_estimator_triangulation.py
Reproduces results/s0.1_snz_triangulation/2026-06-15_writedown.txt (seeds 7, 13).
"""
from __future__ import annotations
import warnings
import numpy as np
import powerlaw

warnings.filterwarnings("ignore")


def gw_profiles(m, k, rng, cap=10**6):
    """Poisson(m) Galton–Watson; returns sizes, durations, censored mask, and the
    per-avalanche temporal profile (per-generation population Z_1..Z_T)."""
    S = np.empty(k, np.int64); D = np.empty(k, np.int64); C = np.zeros(k, bool); P = []
    for i in range(k):
        prof = []; s = 0; cur = 1; c = False
        while cur > 0:
            prof.append(cur); s += cur
            if s > cap:
                c = True; break
            cur = int(rng.poisson(m * cur))
        S[i] = s; D[i] = len(prof); C[i] = c; P.append(np.asarray(prof, float))
    return S, D, C, P


def csn(x):
    return float(powerlaw.Fit(x, discrete=True, verbose=False).power_law.alpha)


def snz_binned(s, d, mc=50):
    """Naive binned-mean slope (known-bad baseline)."""
    T, M = [], []
    for t in np.unique(d):
        if (d == t).sum() >= mc:
            T.append(t); M.append(s[d == t].mean())
    return float(np.polyfit(np.log(T), np.log(M), 1)[0])


def snz_curv(s, d, mc=50):
    """Curvature-corrected bulk fit: log⟨S|T⟩ = a + γ logT + b/T  → return γ.
    Lowest DOF (one correction term)."""
    T, M = [], []
    for t in np.unique(d):
        if (d == t).sum() >= mc:
            T.append(t); M.append(s[d == t].mean())
    T = np.array(T, float); M = np.array(M)
    X = np.column_stack([np.ones_like(T), np.log(T), 1.0 / T])
    return float(np.linalg.lstsq(X, np.log(M), rcond=None)[0][1])


def snz_tail(s, d, q=80):
    """Large-T extreme region: OLS of log S on log T over T ≥ qth percentile."""
    thr = np.percentile(d, q); m = d >= thr
    return float(np.polyfit(np.log(d[m]), np.log(s[m]), 1)[0]) if m.sum() >= 50 else np.nan


def snz_collapse(d, P, C, Tmin=5, K=20, gammas=np.linspace(1.4, 2.5, 23)):
    """Avalanche shape-collapse on profiles; γ minimizes relative collapse error.
    NOTE: reads the profile, not S — so blind to an S–T shuffle look-alike."""
    byT = {}
    for t, p, c in zip(d, P, C):
        if c or t < Tmin:
            continue
        byT.setdefault(int(t), []).append(p)
    xg = np.linspace(0, 1, K); mean = {}
    for t, pl in byT.items():
        if len(pl) >= 30:
            mp = np.mean(np.array(pl), axis=0)
            mean[t] = np.interp(xg, np.linspace(0, 1, t), mp)
    if len(mean) < 4:
        return np.nan
    Ts = np.array(sorted(mean)); Mtx = np.array([mean[t] for t in Ts])
    best = None
    for g in gammas:
        sc = Mtx / (Ts[:, None] ** (g - 1)); m = sc.mean(0); v = sc.var(0)
        err = (v / (m ** 2 + 1e-12)).mean()
        if best is None or err < best[1]:
            best = (g, err)
    return best[0]


def point_pass(rng):
    print("=== CRITICAL generator: 1/σνz point estimates vs N (target → 2.0, Δ → 0) ===")
    hdr = f"{'N':>7} {'ratio':>6} | {'collapse':>8} {'tail':>6} {'curv':>6} {'binned':>6}"
    print(hdr)
    store = {}
    for N in (20000, 50000, 100000):
        S, D, C, P = gw_profiles(1.0, N, rng); store[N] = (S, D, C, P)
        keep = ~C; s, d = S[keep], D[keep]
        ratio = (csn(d) - 1) / (csn(s) - 1)
        print(f"{N:>7} {ratio:6.3f} | {snz_collapse(D,P,C):8.3f} {snz_tail(s,d):6.3f} "
              f"{snz_curv(s,d):6.3f} {snz_binned(s,d):6.3f}")
    return store


def boot(s, d, B, rng):
    dc = np.empty(B); dt = np.empty(B); vc = np.empty(B); vt = np.empty(B)
    N = len(s)
    for b in range(B):
        idx = rng.integers(0, N, N); ss, dd = s[idx], d[idx]
        ratio = (csn(dd) - 1) / (csn(ss) - 1)     # reselect x_min each replicate
        vc[b] = snz_curv(ss, dd); vt[b] = snz_tail(ss, dd)
        dc[b] = ratio - vc[b]; dt[b] = ratio - vt[b]

    def summ(x):
        lo, hi = np.percentile(x, [2.5, 97.5]); return x.mean(), lo, hi, (hi - lo) / 2
    return summ(dc), summ(dt), summ(vc), summ(vt)


def bootstrap_pass(rng, B=50):
    print("\n=== honest joint bootstrap (reselect x_min), B={} ===".format(B))
    for N in (20000, 50000, 100000):
        S, D, C = gw_profiles(1.0, N, rng)[:3]; keep = ~C; s, d = S[keep], D[keep]
        (dcm, dcl, dch, dchw), (dtm, dtl, dth, dthw), (vc, *_), (vt, *_) = boot(s, d, B, rng)
        print(f" N={N:6d}: curv 1/σνz={vc:.3f} Δ={dcm:+.3f} CI=({dcl:+.3f},{dch:+.3f}) "
              f"hw={dchw:.3f} c0={dcl<=0<=dch} | tail 1/σνz={vt:.3f} Δ={dtm:+.3f} "
              f"CI=({dtl:+.3f},{dth:+.3f}) hw={dthw:.3f} c0={dtl<=0<=dth}")
    S, D, C = gw_profiles(1.0, 50000, rng)[:3]; keep = ~C; s, d = S[keep], D[keep]
    s = s[rng.permutation(len(s))]   # full-shuffle look-alike (breaks S–T pairing)
    (dcm, dcl, dch, _), (dtm, dtl, dth, _), *_ = boot(s, d, B, rng)
    print(f" LOOK-ALIKE shuffle: curv Δ={dcm:+.3f} CI=({dcl:+.3f},{dch:+.3f}) excl0={not(dcl<=0<=dch)}"
          f" | tail Δ={dtm:+.3f} CI=({dtl:+.3f},{dth:+.3f}) excl0={not(dtl<=0<=dth)}")


if __name__ == "__main__":
    point_pass(np.random.default_rng(7))
    bootstrap_pass(np.random.default_rng(13))
