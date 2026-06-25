import numpy as np
from critaudit.sim.controls import spec
from critaudit.sim.controls.deffuant import _pair_update, _grow_tree, simulate_labeled, AbmRun
from critaudit.cascades.extract import post_reply_tree


def test_spec_frozen_constants_consistent():
    # the three plants are ordered sub < crit < super in the order parameter
    assert spec.EPS_LOW < spec.EPS_CRIT < spec.EPS_HIGH
    # the certification band brackets criticality with a forbidden middle
    assert spec.N_TREE_SUB < 1.0 < spec.N_TREE_SUPER
    # the Lomax timing kernel is frozen to the gate's calibration regime (NOT the order parameter)
    assert spec.KERNEL_EPS == 0.35 and spec.KERNEL_C == 1.7
    # the gate read is N-matched at the gof-power floor
    assert spec.N_MATCH >= 16000
    # eps_crit solves k*(2e - e^2) = 1 for Uniform[0,1] init (mean-field critical point)
    p_crit = 2 * spec.EPS_CRIT - spec.EPS_CRIT ** 2
    assert abs(spec.K_REACH * p_crit - 1.0) < 0.05


def test_pair_update_conserves_midpoint_and_moves_together():
    x = np.array([0.2, 0.8])
    _pair_update(x, 0, 1, mu_step=0.5)
    # midpoint (sum) conserved — the invariant the in-place sequencing bug would break
    assert abs((x[0] + x[1]) - 1.0) < 1e-12
    # mu_step=0.5 → both meet at the midpoint
    assert abs(x[0] - 0.5) < 1e-12 and abs(x[1] - 0.5) < 1e-12


def test_pair_update_partial_step_symmetric():
    x = np.array([0.1, 0.9])
    _pair_update(x, 0, 1, mu_step=0.3)
    # both move toward each other by mu_step*gap = 0.24, symmetrically; sum conserved
    assert abs((x[0] + x[1]) - 1.0) < 1e-12
    assert abs(x[0] - 0.34) < 1e-12 and abs(x[1] - 0.66) < 1e-12


def test_grow_tree_subcritical_dies_small():
    # eps tiny → almost no confidence-compatible partners → tree is mostly the root alone
    rng = np.random.default_rng(0)
    x = rng.uniform(0.0, 1.0, size=400)
    sizes = []
    for _ in range(200):
        op = x.copy()
        r = int(rng.integers(0, 400))
        t, ag, par, succ = _grow_tree(op, r, 0.0, eps=0.01, k_reach=4, mu_step=0.5,
                                      kernel_eps=0.35, c=1.7, horizon=float("inf"), rng=rng)
        sizes.append(len(t))
    assert np.mean(sizes) < 1.5            # subcritical: trees barely branch
    assert all(p < i for i, p in enumerate(par) if p >= 0)  # parent precedes child locally


def test_grow_tree_supercritical_giant_bounded_by_population():
    # eps large → most attempts succeed → tree grows to (near) the whole population, then dies
    rng = np.random.default_rng(1)
    x = rng.uniform(0.0, 1.0, size=300)
    op = x.copy()
    t, ag, par, succ = _grow_tree(op, 0, 0.0, eps=0.6, k_reach=4, mu_step=0.5,
                                  kernel_eps=0.35, c=1.7, horizon=float("inf"), rng=rng)
    assert len(t) > 100                    # giant component
    assert len(t) <= 300                   # bounded by the population (one firing per agent per tree)
    assert succ >= len(t) - 1              # successes >= edges (collisions add to successes, not nodes)


def test_grow_tree_times_strictly_after_parent():
    rng = np.random.default_rng(2)
    x = rng.uniform(0.0, 1.0, size=200)
    op = x.copy()
    t, ag, par, succ = _grow_tree(op, 0, 100.0, eps=0.5, k_reach=4, mu_step=0.5,
                                  kernel_eps=0.35, c=1.7, horizon=float("inf"), rng=rng)
    assert t[0] == 100.0                                   # root at news_time
    for i, p in enumerate(par):
        if p >= 0:
            assert t[i] > t[p]                            # Lomax delay d>0 → child strictly after parent


def test_grow_tree_censors_offspring_beyond_horizon():
    # finite observation window: no emitted firing may land at/after horizon (mirrors the reference
    # generators.powerlaw_hawkes `ct < horizon` gate). The heavy-tail Lomax pushes most supercritical
    # offspring out, so the censored tree is strictly smaller than the uncensored one.
    x = np.random.default_rng(3).uniform(0.0, 1.0, size=300)
    H = 5.0
    t_cens, _, _, _ = _grow_tree(x.copy(), 0, 0.0, eps=0.6, k_reach=4, mu_step=0.5,
                                 kernel_eps=0.35, c=1.7, horizon=H, rng=np.random.default_rng(3))
    assert all(ti < H for ti in t_cens)                 # every emitted firing is strictly in-window
    t_unc, _, _, _ = _grow_tree(x.copy(), 0, 0.0, eps=0.6, k_reach=4, mu_step=0.5,
                                kernel_eps=0.35, c=1.7, horizon=float("inf"), rng=np.random.default_rng(3))
    assert len(t_cens) < len(t_unc)                     # censoring drops out-of-window offspring


def _small_run(eps, seed=0):
    return simulate_labeled(eps=eps, horizon=300.0, mu_news=2.0, N=120, k_reach=spec.K_REACH,
                            mu_step=spec.MU_STEP, kernel_eps=spec.KERNEL_EPS, c=spec.KERNEL_C,
                            rng=np.random.default_rng(seed))


def test_simulate_labeled_deterministic():
    a = _small_run(0.3, seed=7)
    b = _small_run(0.3, seed=7)
    assert np.array_equal(a.times, b.times)
    assert np.array_equal(a.root_id, b.root_id)
    assert np.array_equal(a.parent_idx, b.parent_idx)


def test_simulate_labeled_stream_is_valid_for_post_reply_tree():
    run = _small_run(0.3, seed=3)
    assert run.times.size > 0
    assert np.all(np.diff(run.times) >= 0)                          # time-sorted
    p = run.parent_idx
    assert np.all(p[p >= 0] < np.arange(p.size)[p >= 0])           # parent precedes child
    av = post_reply_tree(run.times, run.root_id, run.parent_idx)    # fail-closed validation passes
    assert av.sizes.sum() == run.times.size                         # every event lands in exactly one tree


def test_simulate_labeled_nonstationary_rate():
    # supercritical giant cascades make the event rate strongly time-varying (the μ(t) path's reason
    # to exist). Fano factor of per-window counts >> 1 for HIGH, ~order-1 for the Poisson-ish LOW.
    hi = _small_run(0.45, seed=5)
    edges = np.linspace(0.0, 300.0, 31)
    counts = np.histogram(hi.times, bins=edges)[0]
    fano = counts.var() / max(counts.mean(), 1e-9)
    assert fano > 1.5


def test_simulate_labeled_censors_stream_at_horizon():
    # the whole observed stream is bounded to [0, horizon) — the fix for the uncensored heavy-tail
    # smearing that pushed a supercritical plant's gate window to ~1e7 (HIGH-like eps, short horizon).
    run = simulate_labeled(eps=0.45, horizon=200.0, mu_news=2.0, N=120, k_reach=spec.K_REACH,
                           mu_step=spec.MU_STEP, kernel_eps=spec.KERNEL_EPS, c=spec.KERNEL_C,
                           rng=np.random.default_rng(8))
    assert run.times.size > 0
    assert run.times.max() < 200.0
