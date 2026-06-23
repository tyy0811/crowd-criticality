import numpy as np
import pytest
from critaudit.generators.hawkes_sim import simulate
from critaudit.hawkes.mle import fit
from critaudit.hawkes.residuals import rescaled_residuals


@pytest.mark.slow
def test_wellspecified_not_rejected():
    es = simulate(0.6, 4000.0, mu=0.6, beta=1.0, backend="thinning",
                  rng=np.random.default_rng(10))
    f = fit(es)
    dtau, ks_stat, ks_p = rescaled_residuals(es, f)
    assert dtau.size == es.times.size - 1
    assert abs(dtau.mean() - 1.0) < 0.1   # rescaled increments ~ Exp(1): mean 1
    assert ks_p > 0.01                     # not strongly rejected (weak KS floor)
