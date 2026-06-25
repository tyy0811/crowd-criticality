import numpy as np
from critaudit.sim.controls import spec
from critaudit.sim.controls.deffuant import simulate_labeled
from critaudit.sim.controls.anchors import n_tree, chi


def _run(eps, seed=0):
    return simulate_labeled(eps=eps, horizon=400.0, mu_news=3.0, N=300, k_reach=spec.K_REACH,
                            mu_step=spec.MU_STEP, kernel_eps=spec.KERNEL_EPS, c=spec.KERNEL_C,
                            rng=np.random.default_rng(seed))


def test_n_tree_monotonic_and_crosses_one():
    vals = [n_tree(_run(e, seed=11)) for e in (0.04, 0.134, 0.30)]
    assert vals[0] < vals[1] < vals[2]          # monotonic in eps (P(success) ↑ eps)
    assert vals[0] < 1.0 < vals[2]              # orders the extremes across criticality


def test_n_tree_is_from_bookkeeping_not_reconstruction():
    # the fence: n_tree depends ONLY on the generator's emitted successes/event-count, never on
    # post_reply_tree. Zeroing the structural tree (parent_idx) must NOT change n_tree.
    run = _run(0.30, seed=4)
    import dataclasses
    tampered = dataclasses.replace(run, parent_idx=np.full(run.parent_idx.shape, -1, dtype=np.int64),
                                   root_id=np.arange(run.times.size, dtype=np.int64))
    assert n_tree(tampered) == n_tree(run)


def test_chi_finite():
    assert np.isfinite(chi(_run(0.134, seed=2)))
