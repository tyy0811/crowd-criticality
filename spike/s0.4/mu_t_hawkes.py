"""Piecewise-constant baseline μ(t) Hawkes MLE — the WWS-2019 flexible-immigration tool for a
TIME-VARYING immigration rate (NOT the WFS-2016 renewal-immigration EM, which is a *stationary*
generalization and not the ramp tool). The kernel SHAPE is held fixed (the assumed PowerLawKernel); the
flexibility knob is K, the number of equal-EVENT-COUNT baseline segments (K=1 == the scalar-μ stationary
fit `fit_full`). μ(t)=μ_k on segment k.

READOUT (load-bearing): n̂ FALLING as K rises is EXPECTED — a flexible enough baseline interpolates the
rate and drives n̂→0 for ANY data. Identification is a PLATEAU: a K-range where added flexibility stops
lowering n̂, the IC-selected K (min AIC/BIC) landing in it, AND GoF passing there. The plateau value is
the trustworthy n̂. Monotonic descent with no plateau, or IC-K on the slope, = non-identified (endo/exo
not separable). Compare against a smooth μ(t) basis to harden plateau-vs-descent vs a step artifact.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from critaudit.generators import powerlaw_hawkes


def segment_edges_by_count(times, K, horizon):
    """K contiguous baseline segments of ~equal EVENT COUNT (not equal time — a ramp would starve the
    early segment). Returns (edges[K+1], seg_idx[N]). Time edges sit midway between the boundary events."""
    t = np.sort(np.asarray(times, dtype=float))
    N = t.size
    bnds = [int(round(j * N / K)) for j in range(K + 1)]
    edges = [0.0]
    for j in range(1, K):
        i = min(max(bnds[j], 1), N - 1)
        edges.append(0.5 * (t[i - 1] + t[i]))
    edges.append(float(horizon))
    edges = np.array(edges)
    seg_idx = np.clip(np.searchsorted(edges, t, side="right") - 1, 0, K - 1)
    return edges, seg_idx


def _nll_mu_t(params, times, horizon, a, betas, seg_idx, seg_len):
    """Neg-log-lik (and analytic gradient) of piecewise-μ(t) + n·SOE-kernel. params = [μ_1..μ_K, n].
    Returns (f, grad) for scipy `jac=True`. Reduces to the scalar-μ _nll at K=1."""
    K = seg_len.size
    mus, n = params[:K], params[K]
    if n <= 0 or np.any(mus <= 0):
        return np.inf, np.zeros_like(params)
    t = times
    A = np.zeros((t.size, betas.size))
    for i in range(1, t.size):
        A[i] = np.exp(-betas * (t[i] - t[i - 1])) * (A[i - 1] + 1.0)
    s = A @ a                                            # self-excitation sum per event
    lam = mus[seg_idx] + n * s
    if np.any(lam <= 0):
        return np.inf, np.zeros_like(params)
    comp_coef = np.sum((a / betas) * (1.0 - np.exp(-np.outer(horizon - t, betas))).sum(0))  # ∫self / n
    f = -(np.sum(np.log(lam)) - np.sum(mus * seg_len) - n * comp_coef)
    invlam = 1.0 / lam
    g_mu = seg_len - np.bincount(seg_idx, weights=invlam, minlength=K)
    g_n = comp_coef - np.sum(s * invlam)
    return f, np.concatenate([g_mu, [g_n]])


def fit_mu_t(times, horizon, kernel, K, n0=0.5):
    """Fit (μ_1..μ_K, n) by L-BFGS-B (analytic gradient), multi-start in n. Returns a dict with n, mus,
    log-lik, AIC, BIC (p=K+1 params), and the segment edges. IC-select K = argmin AIC/BIC over a sweep."""
    a, betas = kernel.soe()
    t = np.sort(np.asarray(times, dtype=float))
    edges, seg_idx = segment_edges_by_count(t, K, horizon)
    seg_len = np.diff(edges)
    counts = np.bincount(seg_idx, minlength=K).astype(float)
    mu0 = np.maximum(counts / np.maximum(seg_len, 1e-9) * 0.5, 1e-6)
    bounds = [(1e-9, None)] * K + [(1e-9, None)]
    best = None
    for nn in (0.2, 0.5, 0.8):
        x0 = np.concatenate([mu0, [nn]])
        r = minimize(_nll_mu_t, x0, args=(t, horizon, a, betas, seg_idx, seg_len),
                     method="L-BFGS-B", jac=True, bounds=bounds)
        best = r if best is None or r.fun < best.fun else best
    ll = -float(best.fun)
    p = K + 1
    return dict(n=float(best.x[K]), mus=best.x[:K], ll=ll,
                aic=2 * p - 2 * ll, bic=p * np.log(t.size) - 2 * ll, edges=edges, K=K)


def _nll_mu_t_linear(params, times, horizon, a, betas, knots):
    """Neg-log-lik + analytic gradient for a CONTINUOUS piecewise-LINEAR baseline μ(t) (the smooth
    second form). params = [m_0..m_K, n] = μ at the K+1 knots, n. μ(t) linear between knots; ∫μ via
    trapezoid. A linear piece absorbs within-piece TREND (so it cannot be charged to n̂ as the constant
    basis can) -> the targeted test of whether the step basis structurally hid a plateau."""
    K = knots.size - 1
    m, n = params[:K + 1], params[K + 1]
    if n <= 0 or np.any(m <= 0):
        return np.inf, np.zeros_like(params)
    t = times
    A = np.zeros((t.size, betas.size))
    for i in range(1, t.size):
        A[i] = np.exp(-betas * (t[i] - t[i - 1])) * (A[i - 1] + 1.0)
    s = A @ a
    L = np.diff(knots)
    seg = np.clip(np.searchsorted(knots, t, side="right") - 1, 0, K - 1)
    w = (t - knots[seg]) / L[seg]                        # interp weight within piece
    lam = (1.0 - w) * m[seg] + w * m[seg + 1] + n * s
    if np.any(lam <= 0):
        return np.inf, np.zeros_like(params)
    comp_coef = np.sum((a / betas) * (1.0 - np.exp(-np.outer(horizon - t, betas))).sum(0))
    comp_mu = np.sum(0.5 * (m[:-1] + m[1:]) * L)
    f = -(np.sum(np.log(lam)) - comp_mu - n * comp_coef)
    invlam = 1.0 / lam
    g_m = np.zeros(K + 1)
    np.add.at(g_m, np.arange(K), 0.5 * L)                # ∂comp_mu/∂m: piece k -> knots k, k+1
    np.add.at(g_m, np.arange(1, K + 1), 0.5 * L)
    np.add.at(g_m, seg, -(1.0 - w) * invlam)             # -∂loglik/∂m at left knot
    np.add.at(g_m, seg + 1, -w * invlam)                 # -∂loglik/∂m at right knot
    g_n = comp_coef - np.sum(s * invlam)
    return f, np.concatenate([g_m, [g_n]])


def fit_mu_t_linear(times, horizon, kernel, K, n0=0.5):
    """MLE of (μ at K+1 knots, n) with a continuous piecewise-LINEAR baseline. Knots at equal-event-count
    positions. Returns the same dict shape as fit_mu_t (n, mus=knot values, ll, aic, bic, edges=knots, K)."""
    a, betas = kernel.soe()
    t = np.sort(np.asarray(times, dtype=float))
    knots = segment_edges_by_count(t, K, horizon)[0]
    loc = np.empty(K + 1)
    for j in range(K + 1):
        lo, hi = knots[max(j - 1, 0)], knots[min(j + 1, K)]
        loc[j] = np.sum((t >= lo) & (t < hi)) / max(hi - lo, 1e-9) * 0.5
    m0 = np.maximum(loc, 1e-6)
    bounds = [(1e-9, None)] * (K + 1) + [(1e-9, None)]
    best = None
    for nn in (0.2, 0.5, 0.8):
        x0 = np.concatenate([m0, [nn]])
        r = minimize(_nll_mu_t_linear, x0, args=(t, horizon, a, betas, knots),
                     method="L-BFGS-B", jac=True, bounds=bounds)
        best = r if best is None or r.fun < best.fun else best
    ll = -float(best.fun)
    p = K + 2
    return dict(n=float(best.x[K + 1]), mus=best.x[:K + 1], ll=ll,
                aic=2 * p - 2 * ll, bic=p * np.log(t.size) - 2 * ll, edges=knots, K=K)


def fit_mu_only(times, horizon, kernel, n, K):
    """μ(t)-knot MLE with kernel shape AND branching ratio n BOTH FIXED (convex in μ -> single start).
    For the PROFILE likelihood over n: profile_ll(n) = max over shape of fit_mu_only(...).ll. A shallow
    profile across a wide n range = n non-identified; a profile rising with no interior max = degeneracy."""
    a, betas = kernel.soe()
    t = np.sort(np.asarray(times, dtype=float))
    knots = segment_edges_by_count(t, K, horizon)[0]
    loc = np.empty(K + 1)
    for j in range(K + 1):
        lo, hi = knots[max(j - 1, 0)], knots[min(j + 1, K)]
        loc[j] = np.sum((t >= lo) & (t < hi)) / max(hi - lo, 1e-9) * 0.5
    m0 = np.maximum(loc, 1e-6)

    def fg(m):
        val, g = _nll_mu_t_linear(np.concatenate([m, [n]]), t, horizon, a, betas, knots)
        return val, g[:-1]                                # gradient wrt μ-knots only (n fixed)

    r = minimize(fg, m0, method="L-BFGS-B", jac=True, bounds=[(1e-9, None)] * (K + 1))
    return dict(n=float(n), mus=r.x, ll=-float(r.fun), edges=knots)


def rescaled_times_mu_t_linear(times, m, knots, n, eps, c):
    """Compensator with a continuous piecewise-LINEAR baseline: self part (mu=0) + trapezoidal ∫μ up to
    each t_i (full trapezoids before its piece + a partial trapezoid within it)."""
    t = np.sort(np.asarray(times, dtype=float))
    self_part = powerlaw_hawkes.rescaled_times(t, 0.0, n, eps, c)
    L = np.diff(knots)
    full = 0.5 * (m[:-1] + m[1:]) * L
    cum = np.concatenate([[0.0], np.cumsum(full)])
    seg = np.clip(np.searchsorted(knots, t, side="right") - 1, 0, knots.size - 2)
    w = (t - knots[seg]) / L[seg]
    mu_ti = (1.0 - w) * m[seg] + w * m[seg + 1]
    partial = 0.5 * (m[seg] + mu_ti) * (t - knots[seg])
    return self_part + cum[seg] + partial


def rescaled_times_mu_t(times, mus, edges, n, eps, c):
    """Time-rescaling compensator Λ(t_i) with a PIECEWISE-CONSTANT baseline: the self-excitation part
    (mu=0 call to the power-law compensator) plus the μ(t) integral ∫_0^{t_i} μ(s)ds. diff(Λ) ~ Exp(1)
    iff the piecewise-μ(t) + fixed-shape model fits — so KS(diff, Exp(1)) is the cheap fit-quality D(K)
    for the sweep (no bootstrap)."""
    t = np.sort(np.asarray(times, dtype=float))
    self_part = powerlaw_hawkes.rescaled_times(t, 0.0, n, eps, c)        # mu=0 -> pure self compensator
    seg_len = np.diff(edges)
    cum = np.concatenate([[0.0], np.cumsum(mus * seg_len)])              # μ-integral up to each edge
    si = np.clip(np.searchsorted(edges, t, side="right") - 1, 0, mus.size - 1)
    mu_int = cum[si] + mus[si] * (t - edges[si])
    return self_part + mu_int
