import numpy as np
from critaudit.generators.branching import galton_watson
from critaudit.generators.lookalike import scaling_break


def test_full_shuffle_preserves_marginals():
    crit = galton_watson(1.0, 3000, np.random.default_rng(0))
    br = scaling_break(crit, delta=1.0, rng=np.random.default_rng(1))
    keep = ~crit.censored
    assert np.array_equal(np.sort(br.sizes), np.sort(crit.sizes[keep]))
    assert np.array_equal(np.sort(br.durations), np.sort(crit.durations[keep]))


def test_full_shuffle_breaks_pairing():
    crit = galton_watson(1.0, 3000, np.random.default_rng(0))
    br = scaling_break(crit, delta=1.0, rng=np.random.default_rng(2))
    keep = ~crit.censored
    # correlation between size and duration collapses toward 0
    c0 = np.corrcoef(crit.sizes[keep], crit.durations[keep])[0, 1]
    c1 = np.corrcoef(br.sizes, br.durations)[0, 1]
    assert c0 > 0.3 and abs(c1) < 0.1
