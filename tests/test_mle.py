import numpy as np
import pytest
from critaudit.generators.hawkes_sim import simulate
from critaudit.hawkes.mle import fit
from critaudit.types import EventStream


def test_recovers_planted_n():
    es = simulate(0.5, 4000.0, mu=0.6, beta=1.0, backend="thinning",
                  rng=np.random.default_rng(7))
    f = fit(es)
    assert abs(f.n - 0.5) < 0.12
    assert f.mu > 0 and f.beta > 0


def test_unconstrained_n_positive():
    es = simulate(0.9, 3000.0, mu=0.6, beta=1.0, backend="cluster",
                  rng=np.random.default_rng(8))
    f = fit(es)
    assert f.n > 0  # optimizer does not impose n < 1


def test_profile_ci_contains_planted_n():
    es = simulate(0.5, 5000.0, mu=0.6, beta=1.0, backend="thinning",
                  rng=np.random.default_rng(9))
    f = fit(es)
    lo, hi = f.ci
    assert lo < f.n < hi
    assert lo <= 0.5 <= hi


def test_fit_rejects_too_few_events():
    es = EventStream(times=np.array([0.1, 0.2, 0.3, 0.4, 0.5]), horizon=1.0)
    with pytest.raises(ValueError):
        fit(es)
