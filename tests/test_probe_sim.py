"""probe.simulate_probed (sub-inc-3 T3): the UNCONDITIONAL golden byte-identity tripwire vs
simulate_labeled + retention invariants + eligibility/equal-support rules. Fast tier: small
horizons; the operator identity, not statistical power, is what these certify."""
import numpy as np
import pytest

from critaudit.sim.controls import spec as cs
from critaudit.sim.controls.deffuant import simulate_labeled
from critaudit.sim.controls.probe import (
    ProbeRun, eligible_marker_indices, select_equal_support, simulate_probed)

_KW = dict(N=cs.N_AGENTS, k_reach=cs.K_REACH, mu_step=cs.MU_STEP,
           kernel_eps=cs.KERNEL_EPS, c=cs.KERNEL_C)

# One combo per plant + a near-empty run: the tripwire is UNCONDITIONAL — every invocation
# shape must be byte-identical, which is the guarantee that retention cannot perturb the
# measured substrate (design §2).
_COMBOS = [
    (cs.EPS_LOW, 300.0, 2.0, 11),
    (cs.EPS_CRIT, 300.0, 0.8, 12),
    (cs.EPS_HIGH, 200.0, 0.4, 13),
    (cs.EPS_CRIT, 50.0, 0.005, 14),          # near-empty (possibly zero immigrants)
]


@pytest.mark.parametrize("eps,horizon,mu_news,seed", _COMBOS)
def test_golden_byte_identity_with_simulate_labeled(eps, horizon, mu_news, seed):
    a = simulate_labeled(eps, horizon, mu_news, rng=np.random.default_rng(seed), **_KW)
    p = simulate_probed(eps, horizon, mu_news, rng=np.random.default_rng(seed), **_KW)
    for field in ("times", "root_id", "parent_idx", "belief_traj"):
        av, pv = getattr(a, field), getattr(p, field)
        assert av.dtype == pv.dtype and np.array_equal(av, pv), field
    assert a.successes == p.successes


@pytest.mark.parametrize("eps,horizon,mu_news,seed", _COMBOS[:3])
def test_retention_invariants(eps, horizon, mu_news, seed):
    p = simulate_probed(eps, horizon, mu_news, rng=np.random.default_rng(seed), **_KW)
    n_imm = p.tree_news_time.size
    assert (p.tree_size.size == p.tree_successes.size == p.tree_root_agent.size
            == p.tree_root_sorted.size == n_imm)
    assert int(p.tree_size.sum()) == p.times.size            # every event belongs to one tree
    assert int(p.tree_successes.sum()) == p.successes        # aggregate = sum of retained
    assert np.all(p.tree_size >= 1)                          # the root itself is always in-window
    assert np.array_equal(p.tree_news_time, np.sort(p.tree_news_time))
    # Per-root cross-check: retained size == the free root_id-mask count, root by root.
    for r in range(n_imm):
        assert int(np.sum(p.root_id == p.tree_root_sorted[r])) == p.tree_size[r]
        assert p.parent_idx[p.tree_root_sorted[r]] == -1     # the root is an immigrant


def test_eligibility_and_equal_support_rules():
    p = simulate_probed(cs.EPS_CRIT, 300.0, 0.8, rng=np.random.default_rng(12), **_KW)
    idx = eligible_marker_indices(p, t_burn=100.0, t_tail_guard=50.0, horizon=300.0)
    nt = p.tree_news_time[idx]
    assert np.all((nt >= 100.0) & (nt < 250.0))
    # equal support: first-M by news-time order, deterministic
    m = max(1, idx.size - 2)
    sel = select_equal_support(p, m_eligible=m, t_burn=100.0, t_tail_guard=50.0, horizon=300.0)
    assert np.array_equal(sel, idx[:m])
    # thin run fails loudly (fail-closed; design §3)
    with pytest.raises(RuntimeError, match="thin run"):
        select_equal_support(p, m_eligible=idx.size + 1,
                             t_burn=100.0, t_tail_guard=50.0, horizon=300.0)


def test_rng_required():
    with pytest.raises(ValueError, match="rng"):
        simulate_probed(cs.EPS_CRIT, 100.0, 0.5, rng=None, **_KW)


def test_probe_run_is_dataclass_with_expected_fields():
    fields = set(ProbeRun.__dataclass_fields__)
    assert fields == {"times", "root_id", "parent_idx", "belief_traj", "successes",
                      "tree_news_time", "tree_root_agent", "tree_size", "tree_successes",
                      "tree_root_sorted"}
