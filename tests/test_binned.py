import numpy as np
import pytest

from critaudit.hawkes.binned import ExpKernel, PowerLawKernel, _nll, fit_binned, fit_full, certify_granularity
from critaudit.generators.hawkes_sim import simulate
from critaudit.generators import powerlaw_hawkes

# Full recovery validation (the granularity verdict) lives in stage1/granularity; these package tests
# confirm the production estimator is CORRECT and runs — fast and CI-safe.


def test_kernels_have_unit_mass_soe():
    # Modular interface contract: each kernel's SOE shape integrates to 1 (sum a/beta == 1), so the
    # fitted scale IS the branching ratio. Exponential and power-law plug in identically.
    for kernel in (ExpKernel(beta=0.5), PowerLawKernel(eps=0.4, c=0.5), PowerLawKernel(eps=0.3, c=0.25)):
        a, betas = kernel.soe()
        assert abs(float((a / betas).sum()) - 1.0) < 1e-6


def test_nll_prefers_true_branching_ratio():
    # Deterministic: on clean data the SOE likelihood is lower (better) at the true n than at a wrong,
    # near-critical n — anchors the likelihood without the slow MCEM.
    es = simulate(0.6, 1000.0, mu=0.6, beta=0.5, rng=np.random.default_rng(0))
    a, betas = ExpKernel(beta=0.5).soe()
    nll_true = _nll([0.6, 0.6], es.times, 1000.0, a, betas)
    nll_wrong = _nll([0.6, 0.95], es.times, 1000.0, a, betas)
    assert np.isfinite(nll_true) and nll_true < nll_wrong


@pytest.mark.slow
def test_fit_binned_smoke_recovers_in_range():
    # Small-config smoke: the production estimator runs end-to-end and recovers n in a plausible band
    # (binned-Poisson would read ~0.9 here). Tight recovery is validated at scale in stage1.
    es = simulate(0.6, 200.0, mu=0.6, beta=0.5, rng=np.random.default_rng(1))
    nb = int(np.ceil(200.0 / 2.0))
    counts = np.histogram(es.times, bins=np.arange(nb + 1) * 2.0)[0].astype(float)
    fit = fit_binned(counts, 2.0, 200.0, ExpKernel(beta=0.5), np.random.default_rng(7),
                     em_iters=10, sweeps=2)
    assert 0.35 < fit.n < 0.85
    assert 0.0 <= fit.acceptance <= 1.0 and fit.ess > 0
    assert len(fit.trajectory) == 10


@pytest.mark.slow
def test_certify_granularity_runs():
    # The certification harness: full-timing n̂ vs binned-MCEM n̂. On real source-B data (sub-2 s match
    # timestamps) this IS the real-data granularity certification. Smoke: runs and returns a consistent cert.
    es = simulate(0.6, 150.0, mu=0.6, beta=0.5, rng=np.random.default_rng(2))
    cert = certify_granularity(es.times, 2.0, 150.0, ExpKernel(beta=0.5),
                               np.random.default_rng(3), em_iters=8, sweeps=2)
    assert np.isfinite(cert.n_full) and np.isfinite(cert.n_binned)
    assert abs(cert.diff - (cert.n_binned - cert.n_full)) < 1e-9


def test_powerlaw_generator_residuals_are_exp1():
    # The promoted power-law generator: Ogata residuals via the exact compensator are ~ Exp(1).
    t = powerlaw_hawkes.simulate(0.6, 3000.0, 0.4, 0.4, 0.5, np.random.default_rng(0))
    resid = np.diff(powerlaw_hawkes.rescaled_times(t, 0.4, 0.6, 0.4, 0.5))
    assert 0.85 < resid.mean() < 1.15            # ~1.0 if the generator matches the model
    assert t.size > 1000


@pytest.mark.slow
def test_fit_full_matches_certify_granularity_n_full():
    # The gate must judge the EXACT fit the cert reports -> fit_full's n == certify's n_full, bit-for-bit.
    t = powerlaw_hawkes.simulate(0.6, 600.0, 0.4, 0.4, 0.5, np.random.default_rng(0))
    k = PowerLawKernel(eps=0.4, c=0.5)
    _, n = fit_full(t, 600.0, k)
    cert = certify_granularity(t, 2.0, 600.0, k, np.random.default_rng(1), em_iters=6, sweeps=2)
    assert abs(n - cert.n_full) < 1e-9


def test_fit_full_tolerates_ms_ties():
    # Ties (Δt=0) are the original `inf` failure family. The continuous full fit must stay finite and
    # sane even with many trades at the EXACT same instant (multi-fill matches at ms resolution).
    t = powerlaw_hawkes.simulate(0.7, 800.0, 0.3, 0.5, 1.0, np.random.default_rng(0))
    mid = t[t.size // 2]
    t_tied = np.sort(np.concatenate([t, np.full(25, mid)]))   # 25 trades at one instant
    mu, n = fit_full(t_tied, 800.0, PowerLawKernel(eps=0.5, c=1.0))
    assert np.isfinite(mu) and np.isfinite(n)
    assert 0.0 < n < 1.0 and mu > 0.0


@pytest.mark.slow
def test_certify_granularity_accepts_precomputed_n_full():
    # The driver already has n_full from fit_full; passing it in must skip the second full MLE and give
    # a bit-identical cert vs recomputing (deterministic fit_full).
    t = powerlaw_hawkes.simulate(0.6, 600.0, 0.4, 0.4, 0.5, np.random.default_rng(0))
    k = PowerLawKernel(eps=0.4, c=0.5)
    n_full = fit_full(t, 600.0, k)[1]
    c_recompute = certify_granularity(t, 2.0, 600.0, k, np.random.default_rng(1), em_iters=4, sweeps=2)
    c_passed = certify_granularity(t, 2.0, 600.0, k, np.random.default_rng(1), n_full=n_full,
                                   em_iters=4, sweeps=2)
    assert c_recompute.n_full == c_passed.n_full == n_full
    assert abs(c_recompute.diff - c_passed.diff) < 1e-12   # same rng + same n_full -> identical
