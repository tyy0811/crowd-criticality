import numpy as np
from critaudit.generators.powerlaw_hawkes import simulate, simulate_labeled


def test_simulate_labeled_rng_identical_deep_tree():
    # THE load-bearing invariant: labeled and unlabeled consume the RNG IDENTICALLY, so the labels
    # describe the SAME realization. Zero-tolerance equality on a DEEP tree (high n, long horizon) where
    # a perturbed draw sequence actually bites — a shallow stream could coincidentally match.
    for seed in (0, 1, 7, 42):
        rng_a = np.random.default_rng(seed)
        rng_b = np.random.default_rng(seed)
        t_plain = simulate(0.92, 8000.0, 0.05, 0.35, 1.7, rng_a)        # deep: n=0.92, ~thousands of events
        t_lab, root, parent = simulate_labeled(0.92, 8000.0, 0.05, 0.35, 1.7, rng_b)
        assert np.array_equal(t_plain, t_lab)                          # zero tolerance, not allclose
        assert t_lab.size > 500                                        # confirm the tree is actually deep


def test_simulate_labeled_well_formed():
    rng = np.random.default_rng(3)
    t, root, parent = simulate_labeled(0.8, 5000.0, 0.05, 0.35, 1.7, rng)
    N = t.size
    assert root.shape == (N,) and parent.shape == (N,)
    assert (parent[parent >= 0] < np.arange(N)[parent >= 0]).all()     # parent strictly precedes child (sorted)
    assert (root[parent < 0] == np.arange(N)[parent < 0]).all()        # immigrants are their own root
    # every event's root is reachable by walking parents to an immigrant
    for i in range(N):
        j = i
        while parent[j] >= 0:
            j = parent[j]
        assert root[i] == j


def test_simulate_labeled_rng_state_identical_after_call():
    # STRONGER than output equality: the post-call RNG STATE must match -> simulate_labeled consumes the
    # EXACT same draws as simulate (no label-only draw AFTER t_lab is produced, which array_equal on the
    # time stream alone would miss). review 2026-06-24.
    for seed in (0, 1, 42):
        a = np.random.default_rng(seed)
        b = np.random.default_rng(seed)
        simulate(0.92, 8000.0, 0.05, 0.35, 1.7, a)
        simulate_labeled(0.92, 8000.0, 0.05, 0.35, 1.7, b)
        assert a.bit_generator.state == b.bit_generator.state     # identical TOTAL rng consumption
        assert a.random() == b.random()                           # and the next draw agrees


def test_simulate_labeled_rng_identical_on_edge_regimes():
    # Zero-immigrant (tiny mu) and c=0 (degenerate/tied offspring delays) still consume the rng
    # IDENTICALLY -> array_equal + state match where empties/ties could hide a perturbation. review.
    base = dict(n=0.8, horizon=3000.0, mu=0.05, eps=0.35, c=1.7)
    for override in (dict(mu=1e-9), dict(c=0.0)):
        kw = {**base, **override}
        a = np.random.default_rng(5)
        b = np.random.default_rng(5)
        t_plain = simulate(kw["n"], kw["horizon"], kw["mu"], kw["eps"], kw["c"], a)
        t_lab, root, parent = simulate_labeled(kw["n"], kw["horizon"], kw["mu"], kw["eps"], kw["c"], b)
        assert np.array_equal(t_plain, t_lab)
        assert a.bit_generator.state == b.bit_generator.state
