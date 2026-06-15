import numpy as np, powerlaw
from critaudit.powerlaw.csn import fit_powerlaw


def test_recovers_exponent_and_passes():
    x = powerlaw.Power_Law(xmin=1, parameters=[2.5], discrete=True).generate_random(5000)
    f = fit_powerlaw(x, rng=np.random.default_rng(0), n_boot=50)
    assert 2.3 < f.exponent < 2.7
    assert f.passes is True


def test_truncated_sample_fails_via_lrt():
    rng = np.random.default_rng(1)
    # power-law body with a hard exponential cutoff -> truncated favoured
    x = powerlaw.Power_Law(xmin=1, parameters=[2.0], discrete=True).generate_random(8000)
    x = x[x < 40]  # impose a cutoff
    f = fit_powerlaw(x, rng=rng, n_boot=50)
    R, p = f.lrt["truncated_power_law"]
    assert R < 0 and p < 0.05
    assert f.passes is False
