"""S0.1 adversarial-round verification: the bias-floor and shape-collapse findings revisited.

An adversarial cross-review round (5 blind reviewers) charged that two of the brief's
findings were artifacts of implementation choices, not properties of the data. This script
is the OWNER's independent re-derivation (not the reviewers' scratch adv_*.py), confirming:

  CHECK A — correction-form sensitivity + multi-seed: the "Δ≈0.09 bias floor" that motivated
    the reference-differenced null is largely (a) single-seed noise and (b) a 1/T-correction
    choice. With 6 seeds, curv's Δ ≈ +0.03 (consistent with 0). AIC prefers 1/√T, but 1/√T
    makes the scaling relation FAIL (Δ≈−0.16) because the CSN marginal ratio is itself
    finite-size-biased to ~1.90 — the relation closes via MUTUAL bias consistency, so
    "pick the form that closes it" is the Δ-tuning trap one level over.

  CHECK B — profile-estimator objectives: the shipped shape-collapse objective (relative-CV)
    is biased/stuck at 1.65; a standard objective (global-normalized MSD) and peak-height
    give 1.82–1.90. Finding 2 ("shape-collapse measured worst") was an unfair implementation,
    not a property of the method — though all estimators remain biased low at 100k on GW.

Run: python verification/s0.1_snz_redo_diagnostics.py
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


def gw_profiles(m, k, rng, cap=10**6):
    D = []; P = []
    for i in range(k):
        pr = []; s = 0; cur = 1
        while cur > 0:
            pr.append(cur); s += cur
            if s > cap:
                break
            cur = int(rng.poisson(m * cur))
        if s <= cap:
            D.append(len(pr)); P.append(np.asarray(pr, float))
    return np.array(D), P


def csn(x):
    return float(powerlaw.Fit(x, discrete=True, verbose=False).power_law.alpha)


def binned(s, d, mc=50):
    T, M = [], []
    for t in np.unique(d):
        if (d == t).sum() >= mc:
            T.append(t); M.append(s[d == t].mean())
    return np.array(T, float), np.array(M)


_FORMS = {
    "naive":  lambda T: [np.ones_like(T), np.log(T)],
    "1/T":    lambda T: [np.ones_like(T), np.log(T), 1 / T],
    "1/sqrtT": lambda T: [np.ones_like(T), np.log(T), 1 / np.sqrt(T)],
    "1/T2":   lambda T: [np.ones_like(T), np.log(T), 1 / T ** 2],
    "logT/T": lambda T: [np.ones_like(T), np.log(T), np.log(T) / T],
}


def _fit(T, M, form):
    X = np.column_stack(_FORMS[form](T)); y = np.log(M)
    c = np.linalg.lstsq(X, y, rcond=None)[0]
    rss = float(np.sum((y - X @ c) ** 2)); n = len(y)
    return c[1], n * np.log(rss / n) + 2 * X.shape[1]   # gamma, AIC


def check_A(seeds=range(1, 7)):
    print("=== CHECK A: correction-form sensitivity + multi-seed (Δ relative to the CSN ratio) ===")
    for N in (100000, 200000):
        ratios = []; g = {f: [] for f in _FORMS}; a = {f: [] for f in _FORMS}
        for sd in seeds:
            s, d = gw(1.0, N, np.random.default_rng(sd))
            ratios.append((csn(d) - 1) / (csn(s) - 1))
            T, M = binned(s, d)
            for f in _FORMS:
                gg, aa = _fit(T, M, f); g[f].append(gg); a[f].append(aa)
        print(f"--- N={N}: ratio = {np.mean(ratios):.3f} ± {np.std(ratios):.3f} ---")
        for f in _FORMS:
            gs = np.array(g[f])
            print(f"  {f:8s}: γ={gs.mean():.3f}±{gs.std():.3f}  Δ={np.mean(ratios)-gs.mean():+.3f}  AIC={np.mean(a[f]):.1f}")
        print(f"  AIC-best form: {min(_FORMS, key=lambda f: np.mean(a[f]))}")


def _meanprofs(D, P, Tmin=5, K=20, mincnt=30):
    byT = {}
    for t, p in zip(D, P):
        if t >= Tmin:
            byT.setdefault(int(t), []).append(p)
    xg = np.linspace(0, 1, K); mp = {}
    for t, pl in byT.items():
        if len(pl) >= mincnt:
            mp[t] = np.interp(xg, np.linspace(0, 1, t), np.mean(pl, axis=0))
    Ts = np.array(sorted(mp))
    return Ts, np.array([mp[t] for t in Ts])


def check_B():
    print("\n=== CHECK B: profile-based 1/σνz estimators on GW (true = 2.0) ===")
    print(f"{'N':>7} {'relcv(shipped)':>14} {'msd(standard)':>14} {'peak':>6} {'area':>6}")
    for N in (50000, 100000):
        Ts, M = _meanprofs(*gw_profiles(1.0, N, np.random.default_rng(7)))

        def collapse(obj, gammas=np.linspace(1.3, 2.6, 53)):
            best = None
            for gg in gammas:
                sc = M / (Ts[:, None] ** (gg - 1)); m = sc.mean(0); v = sc.var(0)
                err = (v / (m ** 2 + 1e-12)).mean() if obj == "relcv" else v.mean() / (m.mean() ** 2 + 1e-12)
                if best is None or err < best[1]:
                    best = (gg, err)
            return best[0]
        peak = np.polyfit(np.log(Ts), np.log(M.max(1)), 1)[0] + 1.0
        area = np.polyfit(np.log(Ts), np.log(M.sum(1) * Ts / (M.shape[1] - 1)), 1)[0]
        print(f"{N:>7} {collapse('relcv'):>14.3f} {collapse('msd'):>14.3f} {peak:>6.3f} {area:>6.3f}")


if __name__ == "__main__":
    check_A()
    check_B()
