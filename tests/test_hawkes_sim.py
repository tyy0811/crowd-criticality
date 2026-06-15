import numpy as np
from critaudit.generators.hawkes_sim import simulate, choose_backend
from critaudit.types import EventStream


def test_choose_backend():
    assert choose_backend(0.6) == "thinning"
    assert choose_backend(0.95) == "cluster"
    assert choose_backend(0.95, "thinning") == "thinning"


def test_thinning_returns_eventstream():
    es = simulate(0.6, 2000.0, backend="thinning", rng=np.random.default_rng(0))
    assert isinstance(es, EventStream)
    assert es.times.size > 0 and np.all(np.diff(es.times) > 0)


def test_thinning_rate_matches_theory():
    # stationary rate = mu/(1-n); expected N ~ rate*horizon
    es = simulate(0.5, 4000.0, mu=0.6, beta=1.0, backend="thinning",
                  rng=np.random.default_rng(1))
    expected = 0.6 / (1 - 0.5) * 4000.0
    assert 0.8 * expected < es.times.size < 1.2 * expected
