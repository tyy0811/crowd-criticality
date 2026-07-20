"""GW positive control for the probe-recoverability gate (sub-inc-3 T5, @slow, $0).

Exact Galton-Watson substrate: Binomial(K_REACH, p) offspring with p = 2*eps - eps^2 (so the
known branching m = K_REACH*(2*eps - eps^2) crosses 1 exactly at EPS_CRIT, by that constant's
own construction), NO collisions, NO censoring; the finite-population role is played by a hard
size cap at N_AGENTS (the substrate's own ceiling). Ground truth n_gen = the KNOWN m (constant
across seeds — that is what makes this a positive control).

Purpose (design §4): (i) instrument-not-defect — the exact-GW case must PASS the frozen gate, so
an ABM failure is a property of the collision/censor operator, not of the instrument; (ii)
POWER-CERTIFICATION of the frozen M_ELIGIBLE x N_SEEDS budgets BEFORE any measurement — the
transform must clear at TOL/2 (margin doctrine) and the locator/seed-consistency must clear at
these exact budgets. A failure here means budgets rise pre-measurement (a recorded spec change),
never post hoc."""
import numpy as np
import pytest

from critaudit.sim.controls import probe_spec as pspec
from critaudit.sim.controls import spec as cs
from critaudit.sim.controls.probe_gate import evaluate_recoverability


def _gw_sizes(m_trees, p, k, cap, rng):
    """Vectorized total-progeny sizes of m_trees independent GW trees, Binomial(k, p) offspring,
    hard size cap (finite-population stand-in). Returns int array (m_trees,)."""
    sizes = np.ones(m_trees, dtype=np.int64)
    active = np.ones(m_trees, dtype=np.int64)
    while True:
        alive = (active > 0) & (sizes < cap)
        if not np.any(alive):
            break
        offspring = np.zeros(m_trees, dtype=np.int64)
        offspring[alive] = rng.binomial(active[alive] * k, p)
        room = cap - sizes
        offspring = np.minimum(offspring, np.maximum(room, 0))
        sizes += offspring
        active = offspring
    return sizes


def _control_surface():
    grid = np.asarray(pspec.EPS_GRID)
    n_eps, n_seeds, m_elig = grid.size, pspec.N_SEEDS, pspec.M_ELIGIBLE
    chi = np.empty((n_eps, n_seeds))
    s_mean = np.empty((n_eps, n_seeds))
    n_gen = np.empty((n_eps, n_seeds))
    n_resp = np.empty((n_eps, n_seeds))
    for gi, eps in enumerate(grid):
        p = 2.0 * eps - eps ** 2
        m_true = cs.K_REACH * p                       # the KNOWN ground truth
        for si in range(n_seeds):
            rng = np.random.default_rng(np.random.SeedSequence(
                pspec.SEED_PROBE, spawn_key=(gi, si)))
            S = _gw_sizes(m_elig, p, cs.K_REACH, cs.N_AGENTS, rng)
            chi[gi, si] = S.var(ddof=1) / S.mean() ** 2      # CV^2 (CHI_RESP_STATISTIC; the
            s_mean[gi, si] = S.mean()                        # Var(S) form is displaced
            n_gen[gi, si] = m_true                           # supercritical — spec note)
            n_resp[gi, si] = 1.0 - 1.0 / S.mean()
    used = np.full((n_eps, n_seeds), m_elig, dtype=int)
    return {"eps_grid": grid.tolist(), "chi_resp": chi.tolist(), "s_mean": s_mean.tolist(),
            "n_gen": n_gen.tolist(), "n_resp": n_resp.tolist(), "used_markers": used.tolist()}


@pytest.mark.slow
def test_gw_positive_control_certifies_gate_and_budgets():
    v = evaluate_recoverability(_control_surface())
    # (i) the exact-GW case must PASS the frozen locator gate at the frozen budgets.
    assert v["status"] == "PASS", v["reasons"]
    assert v["locator"]["seed_consistency"] >= pspec.SEED_CONSISTENCY_MIN
    # The known crossing sits at EPS_CRIT by construction; the peak must bracket it.
    assert abs(v["locator"]["eps_c_gen"] - cs.EPS_CRIT) < 0.01
    # (ii) power certification: the transform clears at TOL/2 (margin doctrine) on the exact
    # substrate, where n_resp SHOULD equal m up to sampling noise at these budgets.
    assert v["transform"]["pass"] is True, v["transform"]["reasons"]
    assert all(err <= pspec.N_RESP_TOL / 2 for err in v["transform"]["accuracy_err"].values()), \
        v["transform"]["accuracy_err"]
    # (b2) the resolution floor is EVALUABLE at these budgets (its verdict is recorded; the
    # exact-GW value certifies the noise floor of the estimator itself).
    assert v["resolution"]["band_2sd"], "no band points on the control — grid/budget defect"
