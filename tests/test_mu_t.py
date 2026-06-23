import numpy as np

from critaudit.hawkes.mu_t import segment_edges_by_count, fit_mu_t_linear, fit_mu_only
from critaudit.hawkes.binned import PowerLawKernel, fit_full
from critaudit.generators import powerlaw_hawkes


def test_segment_edges_equal_event_count():
    t = np.sort(np.concatenate([np.linspace(0, 10, 90), np.linspace(10, 12, 10)]))  # front-loaded
    edges, seg = segment_edges_by_count(t, 5, 12.0)
    counts = np.bincount(seg, minlength=5)
    assert edges[0] == 0.0 and edges[-1] == 12.0
    assert counts.max() - counts.min() <= 1            # ~equal COUNT, not equal time


def test_flexible_mu_recovers_under_a_ramp_where_stationary_inflates():
    # THE reason the module exists. On RAMPED genuine n=0.60 (recorded regime), a stationary fit absorbs
    # the ramp into the branching ratio (n̂ ≈ 0.84-0.87, near-critical-looking); the flexible μ(t) absorbs
    # it into the baseline and recovers n̂ ≈ 0.57. Differential, on data confirmed to ramp (Task 1).
    t = powerlaw_hawkes.simulate_ramp(0.60, 32760.0, 0.0142, 0.35, 1.7, 11.0, np.random.default_rng(0))
    k = PowerLawKernel(eps=0.35, c=1.7)
    n_stat = fit_full(t, 32760.0, k)[1]
    n_flex = fit_mu_t_linear(t, 32760.0, k, 8)["n"]
    assert n_stat > 0.78                               # stationary fit inflated toward criticality
    assert n_flex < n_stat - 0.15                      # flexible recovers MEANINGFULLY lower
    assert 0.45 < n_flex < 0.75                        # ...near the planted 0.60


def test_fit_mu_only_is_deterministic_single_optimum():
    # fit_mu_only fixes n + shape, maximizes over μ-knots only (convex) -> re-running gives the same ll.
    # This is the property the profile-over-n (and the gate) rides on.
    t = powerlaw_hawkes.simulate(0.6, 1500.0, 0.4, 0.4, 0.5, np.random.default_rng(1))
    k = PowerLawKernel(eps=0.4, c=0.5)
    a = fit_mu_only(t, float(t[-1]), k, 0.75, 12)["ll"]
    b = fit_mu_only(t, float(t[-1]), k, 0.75, 12)["ll"]
    assert abs(a - b) < 1e-9
