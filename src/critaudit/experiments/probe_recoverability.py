"""Sub-inc-3 driver — the $0 probe-recoverability grid (design §3/§4).

Runs simulate_probed over the frozen EPS_GRID x N_SEEDS design at the FIXED drive
(MU_NEWS_PROBE — the owner's confound correction: one drive across the whole primary surface),
computes the frozen estimators over exactly M_ELIGIBLE equal-support markers per cell, evaluates
the recoverability gate fail-closed, and banks a deterministic JSON. The sensitivity panel
(alternative drives at one dense-window eps) is recorded-not-asserted and NEVER enters any gate.

FIREWALL (design §6, R8): this module imports neither llm_parrot_spec nor cohort_marginals (the
sub-inc-2 scan-set surface) nor any fitting stack; the banked-JSON dump idiom is a LOCAL copy of
the sub-inc-2 pattern, deliberately not imported. Budget: $0 — local CPU only."""
from __future__ import annotations
import json
import os
from multiprocessing import Pool

import numpy as np

from critaudit.sim.controls import probe_spec as pspec
from critaudit.sim.controls import spec as cs
from critaudit.sim.controls.probe import select_equal_support, simulate_probed
from critaudit.sim.controls.probe_gate import evaluate_recoverability

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
BANKED_DIR = os.path.join(_REPO_ROOT, "results", "s3_probe")
BANKED_GRID_JSON = os.path.join(BANKED_DIR, "2026-07-20_probe_recoverability.json")


def _dump_banked_json(record, out_path):
    """Deterministic banked-artifact serialization (local copy of the sub-inc-2 idiom — R8):
    sorted keys, no wall-clock, allow_nan=False (a NaN diagnostic must never silently enter the
    committed record)."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(record, f, sort_keys=True, indent=1, allow_nan=False)
        f.write("\n")


def _cell(args):
    """One (eps_index, seed_index[, mu_news]) cell. Module-level for Pool pickling; every input
    comes from the frozen spec (or the explicit sensitivity-panel drive)."""
    gi, si, eps, mu_news, horizon, m_eligible, t_burn, t_tail = args
    rng = np.random.default_rng(np.random.SeedSequence(pspec.SEED_PROBE, spawn_key=(gi, si)))
    run = simulate_probed(eps, horizon, mu_news, N=cs.N_AGENTS, k_reach=cs.K_REACH,
                          mu_step=cs.MU_STEP, kernel_eps=cs.KERNEL_EPS, c=cs.KERNEL_C, rng=rng)
    sel = select_equal_support(run, m_eligible=m_eligible, t_burn=t_burn,
                               t_tail_guard=t_tail, horizon=horizon)   # raises on thin run
    S = run.tree_size[sel].astype(float)
    succ = run.tree_successes[sel].astype(float)
    s_mean = float(S.mean())
    lag1 = float(np.corrcoef(S[:-1], S[1:])[0, 1]) if S.size >= 3 and S.std() > 0 else 0.0
    return {
        "eps_index": gi, "seed_index": si,
        "chi_resp": float(S.var(ddof=1) / s_mean ** 2),      # CV^2 (CHI_RESP_STATISTIC)
        "s_mean": s_mean,
        "n_gen": float(succ.sum() / S.sum()),
        "n_resp": float(1.0 - 1.0 / s_mean),
        "used_markers": int(S.size),
        # recorded-not-gated diagnostics (incl. the rejected susceptibility variants):
        "var_s": float(S.var(ddof=1)),
        "fano_s": float(S.var(ddof=1) / s_mean),
        "s_median": float(np.median(S)),
        "lag1_autocorr_s": lag1,
        "n_immigrants": int(run.tree_news_time.size),
        "n_eligible": int(np.sum((run.tree_news_time >= t_burn)
                                 & (run.tree_news_time < horizon - t_tail))),
    }


def run_probe_grid(out_path=None, *, n_workers=None, _eps_grid=None, _n_seeds=None,
                   _horizon=None, _m_eligible=None, _with_sensitivity=True):
    """The $0 study at the FROZEN design (the underscore overrides exist ONLY for the reduced-
    budget @slow smoke test and are echoed into the record so a non-frozen run can never
    masquerade as the registered artifact)."""
    eps_grid = tuple(_eps_grid) if _eps_grid is not None else pspec.EPS_GRID
    n_seeds = _n_seeds if _n_seeds is not None else pspec.N_SEEDS
    horizon = _horizon if _horizon is not None else cs.HORIZON
    m_eligible = _m_eligible if _m_eligible is not None else pspec.M_ELIGIBLE
    frozen_design = (eps_grid == pspec.EPS_GRID and n_seeds == pspec.N_SEEDS
                     and horizon == cs.HORIZON and m_eligible == pspec.M_ELIGIBLE)
    t_burn = pspec.T_BURN if frozen_design else horizon * 0.25
    t_tail = pspec.T_TAIL_GUARD if frozen_design else horizon * 0.125

    jobs = [(gi, si, eps, pspec.MU_NEWS_PROBE, horizon, m_eligible, t_burn, t_tail)
            for gi, eps in enumerate(eps_grid) for si in range(n_seeds)]
    sens_jobs = []
    if _with_sensitivity and frozen_design:
        s_gi = eps_grid.index(pspec.SENSITIVITY_EPS)
        # sensitivity cells use DISTINCT spawn keys (offset far beyond the grid) so they can
        # never collide with a primary stream.
        sens_jobs = [(1000 + k, si, pspec.SENSITIVITY_EPS, mu, horizon, m_eligible,
                      t_burn, t_tail)
                     for k, mu in enumerate(pspec.SENSITIVITY_MU_NEWS)
                     for si in range(n_seeds)]
        del s_gi

    with Pool(n_workers) as pool:
        cells = pool.map(_cell, jobs + sens_jobs)
    primary = cells[:len(jobs)]
    sens = cells[len(jobs):]

    def _matrix(key, rows):
        m = [[None] * n_seeds for _ in eps_grid]
        for c in rows:
            m[c["eps_index"]][c["seed_index"]] = c[key]
        return m

    surface = {
        "eps_grid": list(eps_grid),
        "chi_resp": _matrix("chi_resp", primary),
        "s_mean": _matrix("s_mean", primary),
        "n_gen": _matrix("n_gen", primary),
        "n_resp": _matrix("n_resp", primary),
        "used_markers": _matrix("used_markers", primary),
    }
    verdict = (evaluate_recoverability(surface) if frozen_design else
               {"status": "NOT_EVALUATED_NON_FROZEN_DESIGN"})

    record = {
        "artifact": "probe_recoverability",
        "design": pspec.DESIGN_DOC,
        "design_sha256": pspec.DESIGN_DOC_SHA256,
        "frozen_design": frozen_design,
        "spec": {
            "chi_resp_statistic": pspec.CHI_RESP_STATISTIC,
            "mu_news_probe": pspec.MU_NEWS_PROBE,
            "eps_grid": list(eps_grid),
            "n_seeds": n_seeds,
            "m_eligible": m_eligible,
            "horizon": horizon,
            "t_burn": t_burn,
            "t_tail_guard": t_tail,
            "seed_probe": pspec.SEED_PROBE,
            "train_seed_indices": list(pspec.TRAIN_SEED_INDICES),
            "test_seed_indices": list(pspec.TEST_SEED_INDICES),
            "operator_fingerprint": {
                "n_agents": cs.N_AGENTS, "k_reach": cs.K_REACH, "mu_step": cs.MU_STEP,
                "kernel_eps": cs.KERNEL_EPS, "kernel_c": cs.KERNEL_C,
            },
        },
        "surface": surface,
        "diagnostics": {k: _matrix(k, primary)
                        for k in ("var_s", "fano_s", "s_median", "lag1_autocorr_s",
                                  "n_immigrants", "n_eligible")},
        "sensitivity_panel": sens,       # recorded-not-asserted; never enters any gate
        "verdict": verdict,
    }
    if out_path is not None:
        _dump_banked_json(record, out_path)
    return record
