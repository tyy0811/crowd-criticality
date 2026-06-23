"""TDD for the piecewise-constant baseline μ(t) Hawkes MLE (the WWS flexible-immigration tool for a
time-varying rate). The decisive test is ramp-recovery: a KNOWN sub-critical n under a KNOWN ramp must
read inflated at K=1 (scalar μ) and recover the true n on a PLATEAU as K grows -- validating both the
estimator and the plateau readout on ground truth before any real-data run."""
import numpy as np

from critaudit.hawkes.binned import PowerLawKernel, fit_full
from critaudit.generators import powerlaw_hawkes

from mu_t_hawkes import (fit_mu_t, _nll_mu_t, segment_edges_by_count, rescaled_times_mu_t,
                         fit_mu_t_linear, _nll_mu_t_linear, rescaled_times_mu_t_linear, fit_mu_only)


def _simulate_ramp(mu0, ramp, n, T, eps, c, rng):
    """Hawkes with inhomogeneous-Poisson immigrants μ(t)=mu0*(1+ramp*t/T) (thinning) + Lomax offspring.
    Known baseline ramp + known branching ratio n -> ground truth for recovery."""
    mu_max = mu0 * (1.0 + max(ramp, 0.0))
    cand = rng.uniform(0, T, rng.poisson(mu_max * T))
    imm = cand[rng.uniform(0, 1, cand.size) < (mu0 * (1.0 + ramp * cand / T)) / mu_max]
    times, queue = list(imm), list(imm)
    while queue:
        p = queue.pop()
        k = rng.poisson(n)
        if k:
            for ct in p + c * ((1.0 - rng.uniform(0, 1, k)) ** (-1.0 / eps) - 1.0):
                if ct < T:
                    times.append(ct); queue.append(ct)
    return np.sort(np.asarray(times, float))


def test_segment_edges_equal_event_count():
    t = np.sort(np.asarray([0.1, 0.2, 5.0, 9.0, 9.1, 9.2], float))   # bunched late (a "ramp")
    edges, seg_idx = segment_edges_by_count(t, 3, 10.0)
    assert edges[0] == 0.0 and edges[-1] == 10.0 and edges.size == 4
    counts = np.bincount(seg_idx, minlength=3)
    assert counts.tolist() == [2, 2, 2]            # equal EVENT count, NOT equal time


def test_grad_matches_numerical():
    from scipy.optimize import approx_fprime
    t = powerlaw_hawkes.simulate(0.5, 300.0, 0.4, 0.4, 0.5, np.random.default_rng(0))
    a, betas = PowerLawKernel(eps=0.4, c=0.5).soe()
    edges, seg_idx = segment_edges_by_count(t, 3, 300.0)
    seg_len = np.diff(edges)
    x = np.array([0.3, 0.4, 0.5, 0.6])             # mu_1,mu_2,mu_3, n
    f, g = _nll_mu_t(x, t, 300.0, a, betas, seg_idx, seg_len)
    gnum = approx_fprime(x, lambda p: _nll_mu_t(p, t, 300.0, a, betas, seg_idx, seg_len)[0], 1e-6)
    assert np.allclose(g, gnum, rtol=1e-3, atol=1e-3)


def test_K1_matches_scalar_fit_full():
    # K=1 piecewise == the existing scalar-μ full fit (same model).
    t = powerlaw_hawkes.simulate(0.6, 600.0, 0.4, 0.4, 0.5, np.random.default_rng(1))
    k = PowerLawKernel(eps=0.4, c=0.5)
    mu_s, n_s = fit_full(t, 600.0, k)
    r = fit_mu_t(t, 600.0, k, K=1)
    assert abs(r["n"] - n_s) < 1e-3 and abs(r["mus"][0] - mu_s) < 1e-3


def test_stationary_n_plateaus_across_K():
    # Stationary data: adding baseline flexibility should NOT lower n̂ much -> a plateau from K=1 (the
    # identified case). n̂ stays near the true 0.5 across K.
    t = powerlaw_hawkes.simulate(0.5, 4000.0, 0.4, 0.4, 0.5, np.random.default_rng(2))
    k = PowerLawKernel(eps=0.4, c=0.5)
    ns = [fit_mu_t(t, float(t[-1]), k, K=K)["n"] for K in (1, 4, 8, 16)]
    assert max(ns) - min(ns) < 0.15            # flat -> identified, no spurious slide
    assert abs(np.mean(ns) - 0.5) < 0.2


def test_rescaled_mu_t_matches_scalar_when_K1():
    # K=1 (single segment, scalar μ over [0,T]) must reproduce the power-law scalar-μ compensator.
    t = powerlaw_hawkes.simulate(0.6, 600.0, 0.4, 0.4, 0.5, np.random.default_rng(5))
    mu, n, eps, c = 0.4, 0.6, 0.4, 0.5
    scalar = powerlaw_hawkes.rescaled_times(t, mu, n, eps, c)
    piecewise = rescaled_times_mu_t(t, np.array([mu]), np.array([0.0, 600.0]), n, eps, c)
    np.testing.assert_allclose(scalar, piecewise, rtol=1e-9, atol=1e-9)


def test_ramp_recovery_inflated_at_K1_recovers_on_plateau():
    # THE validation: KNOWN sub-critical n=0.3 under a KNOWN 8x ramp. K=1 (scalar μ) must INFLATE n̂;
    # n̂(K) must DESCEND to a plateau near the true 0.3 as K grows (the correction working + the plateau
    # signature). This proves the method recovers true n under non-stationarity AND that the readout is
    # plateau-not-movement.
    t = _simulate_ramp(0.4, 8.0, 0.3, 6000.0, 0.4, 0.5, np.random.default_rng(3))
    k = PowerLawKernel(eps=0.4, c=0.5)
    curve = {K: fit_mu_t(t, 6000.0, k, K=K)["n"] for K in (1, 2, 4, 8, 16, 24)}
    assert curve[1] > 0.45                      # scalar baseline absorbs the ramp into n̂ -> inflated
    plateau = [curve[K] for K in (8, 16, 24)]
    assert abs(np.mean(plateau) - 0.3) < 0.12   # recovers true n on the plateau
    assert max(plateau) - min(plateau) < 0.12   # and it is a PLATEAU (stable across high K)


def test_linear_grad_matches_numerical():
    from scipy.optimize import approx_fprime
    t = powerlaw_hawkes.simulate(0.5, 300.0, 0.4, 0.4, 0.5, np.random.default_rng(0))
    a, betas = PowerLawKernel(eps=0.4, c=0.5).soe()
    knots = segment_edges_by_count(t, 3, 300.0)[0]              # 4 knots
    x = np.array([0.3, 0.4, 0.5, 0.45, 0.6])                    # m_0..m_3, n
    f, g = _nll_mu_t_linear(x, t, 300.0, a, betas, knots)
    gnum = approx_fprime(x, lambda p: _nll_mu_t_linear(p, t, 300.0, a, betas, knots)[0], 1e-6)
    assert np.allclose(g, gnum, rtol=1e-3, atol=1e-3)


def test_linear_constant_knots_match_scalar():
    # all knot values equal -> μ(t) constant -> must match the scalar-μ full fit.
    t = powerlaw_hawkes.simulate(0.6, 600.0, 0.4, 0.4, 0.5, np.random.default_rng(1))
    k = PowerLawKernel(eps=0.4, c=0.5)
    mu_s, n_s = fit_full(t, 600.0, k)
    r = fit_mu_t_linear(t, 600.0, k, K=1)        # 1 piece, 2 knots; linear is a superset of constant μ
    scalar_ll = -_nll_mu_t(np.array([mu_s, n_s]), np.sort(t), 600.0, *k.soe(),
                           np.zeros(t.size, int), np.array([600.0]))[0]
    assert 0.0 < r["n"] < 1.0 and np.all(r["mus"] > 0)
    assert r["ll"] >= scalar_ll - 1e-3           # superset -> at least as good as the constant fit


def test_rescaled_linear_matches_scalar_when_constant():
    t = powerlaw_hawkes.simulate(0.6, 600.0, 0.4, 0.4, 0.5, np.random.default_rng(5))
    mu, n, eps, c = 0.4, 0.6, 0.4, 0.5
    scalar = powerlaw_hawkes.rescaled_times(t, mu, n, eps, c)
    lin = rescaled_times_mu_t_linear(t, np.array([mu, mu]), np.array([0.0, 600.0]), n, eps, c)
    np.testing.assert_allclose(scalar, lin, rtol=1e-9, atol=1e-9)


def test_fit_mu_only_consistent_with_free_fit_at_its_n():
    # Profiling at the free fit's own n̂ must reproduce its log-lik (μ re-optimized at that n) and the
    # free fit must not beat it by more than noise -> validates the n-fixed profile machinery.
    t = powerlaw_hawkes.simulate(0.6, 800.0, 0.4, 0.4, 0.5, np.random.default_rng(8))
    k = PowerLawKernel(eps=0.4, c=0.5)
    free = fit_mu_t_linear(t, 800.0, k, K=4)
    prof = fit_mu_only(t, 800.0, k, n=free["n"], K=4)
    assert abs(prof["ll"] - free["ll"]) < 0.5            # same ll at the free n̂
    # and profiling at a far-off n must be WORSE (lower ll) -> the profile actually varies
    worse = fit_mu_only(t, 800.0, k, n=0.05, K=4)
    assert worse["ll"] < free["ll"]


def test_linear_ramp_recovery_plateaus_earlier():
    # The smooth-basis hardening: piecewise-LINEAR captures a ramp's within-piece trend, so it should
    # recover the true sub-critical n=0.3 and plateau at LOWER K than the constant basis (no within-
    # segment trend left for n̂ to absorb).
    t = _simulate_ramp(0.4, 8.0, 0.3, 6000.0, 0.4, 0.5, np.random.default_rng(3))
    k = PowerLawKernel(eps=0.4, c=0.5)
    curve = {K: fit_mu_t_linear(t, 6000.0, k, K=K)["n"] for K in (2, 4, 8, 16)}
    plateau = [curve[K] for K in (4, 8, 16)]
    assert abs(np.mean(plateau) - 0.3) < 0.12   # recovers true n
    assert max(plateau) - min(plateau) < 0.12   # plateau
