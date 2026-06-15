import numpy as np
from critaudit.generators.hawkes_sim import simulate
from critaudit.hawkes.mle import fit


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
