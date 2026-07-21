"""Instrumented Deffuant driver for the probe-recoverability study (sub-inc-3 design §2).

TAGGED-NATIVE MARKERS: every native news immigrant already IS the standardized micro-injection
(random agent, belief re-randomized Uniform[0,1], identical rule every time — deffuant.py:100-101),
so `simulate_probed` is `simulate_labeled`'s loop with RETENTION added: the per-tree
(news_time, root_agent, tree_size, tree_successes) that simulate_labeled discards. Retention
consumes NO randomness and mutates NO state, so the output AbmRun fields are byte-identical to
`simulate_labeled` on the same rng — enforced by an UNCONDITIONAL golden tripwire test on every
invocation shape, which is the guarantee that probe machinery cannot perturb the measured
substrate. `deffuant.py` itself is untouched (frozen shakedown generator).

Rejected alternatives (design §2): a merged injection schedule (a spawned probe stream keeps
background DRAWS unperturbed but not the shared opinion field — probe successes call _pair_update,
so byte-identical background under active probing is impossible in principle); fixed-belief
markers (a different operator than the substrate's own drive)."""
from __future__ import annotations
from dataclasses import dataclass

import numpy as np

from critaudit.sim.controls.deffuant import _grow_tree


@dataclass
class ProbeRun:
    """AbmRun's five fields (byte-identical to simulate_labeled on the same rng) + per-tree
    retention, one row per immigrant in news-time order."""
    times: np.ndarray          # sorted event times
    root_id: np.ndarray        # int64; each event's cascade root (sorted index)
    parent_idx: np.ndarray     # int64; parent event (sorted index), -1 for immigrants
    belief_traj: np.ndarray    # mean opinion sampled after each tree (news-time order)
    successes: int             # total confidence-compatible attempts (collisions incl.)
    tree_news_time: np.ndarray     # float64, len n_imm — the immigrant's news time
    tree_root_agent: np.ndarray    # int64 — the shocked agent
    tree_size: np.ndarray          # int64 — realized in-window node count incl. root
    tree_successes: np.ndarray     # int64 — generative count incl. collision + censor mass
    tree_root_sorted: np.ndarray   # int64 — the root's SORTED event index (root_id cross-check)


def simulate_probed(eps, horizon, mu_news, *, N, k_reach, mu_step, kernel_eps, c, rng,
                    max_events=500_000):
    """simulate_labeled's exact loop (same signature, same draw order) with per-tree retention.
    Every divergence from deffuant.simulate_labeled's realized arrays is a bug the golden
    tripwire catches — do not 'improve' this loop independently of that one."""
    if rng is None:
        raise ValueError("pass an explicit numpy Generator as rng")
    opinions = rng.uniform(0.0, 1.0, size=N)
    n_imm = int(rng.poisson(mu_news * horizon))
    news_times = np.sort(rng.uniform(0.0, horizon, size=n_imm))
    times, parents, roots = [], [], []
    belief_traj = np.empty(n_imm)
    successes = 0
    tree_root_agent = np.empty(n_imm, dtype=np.int64)
    tree_size = np.empty(n_imm, dtype=np.int64)
    tree_successes = np.empty(n_imm, dtype=np.int64)
    tree_root_gen = np.empty(n_imm, dtype=np.int64)
    for r in range(n_imm):
        root_agent = int(rng.integers(0, N))
        opinions[root_agent] = float(rng.uniform(0.0, 1.0))     # news re-randomizes the agent
        base = len(times)
        t_tree, _ag_tree, par_tree, succ = _grow_tree(opinions, root_agent, float(news_times[r]),
                                                      eps, k_reach, mu_step, kernel_eps, c,
                                                      horizon, rng)
        successes += succ
        for j in range(len(t_tree)):
            times.append(t_tree[j])
            parents.append(-1 if par_tree[j] < 0 else base + par_tree[j])   # gen-index space
            roots.append(base)                                              # tree root's gen-index
        belief_traj[r] = float(opinions.mean())
        tree_root_agent[r] = root_agent                          # retention: no draws, no writes
        tree_size[r] = len(t_tree)
        tree_successes[r] = succ
        tree_root_gen[r] = base
        if len(times) > max_events:
            raise RuntimeError("event explosion — lower mu_news/eps or the per-plant event budget")
    t = np.asarray(times, dtype=float)
    if t.size == 0:
        empty = np.empty(0, dtype=np.int64)
        return ProbeRun(times=t, root_id=empty, parent_idx=empty, belief_traj=belief_traj,
                        successes=0, tree_news_time=news_times,
                        tree_root_agent=tree_root_agent, tree_size=tree_size,
                        tree_successes=tree_successes, tree_root_sorted=empty)
    order = np.argsort(t, kind="stable")                        # gen-order -> time-sorted
    inv = np.empty(t.size, dtype=np.int64)
    inv[order] = np.arange(t.size)
    pg = np.asarray(parents, dtype=np.int64)[order]
    parent_sorted = np.where(pg < 0, -1, inv[np.where(pg < 0, 0, pg)])
    root_sorted = inv[np.asarray(roots, dtype=np.int64)[order]]
    return ProbeRun(times=t[order], root_id=root_sorted, parent_idx=parent_sorted,
                    belief_traj=belief_traj, successes=successes,
                    tree_news_time=news_times, tree_root_agent=tree_root_agent,
                    tree_size=tree_size, tree_successes=tree_successes,
                    tree_root_sorted=inv[tree_root_gen])


def eligible_marker_indices(run, *, t_burn, t_tail_guard, horizon):
    """Frozen eligibility (design §2): immigrant r eligible iff
    t_burn <= tree_news_time[r] < horizon - t_tail_guard. Pure; news-time order preserved."""
    nt = np.asarray(run.tree_news_time)
    return np.flatnonzero((nt >= t_burn) & (nt < horizon - t_tail_guard))


def select_equal_support(run, *, m_eligible, t_burn, t_tail_guard, horizon):
    """EQUAL SUPPORT (design §3): exactly the FIRST m_eligible eligible markers by news_time
    order (deterministic — no selection channel). FAIL-CLOSED on a thin run: fewer eligible
    markers than m_eligible raises rather than contributing unequal support/df."""
    idx = eligible_marker_indices(run, t_burn=t_burn, t_tail_guard=t_tail_guard, horizon=horizon)
    if idx.size < m_eligible:
        raise RuntimeError(
            f"thin run: {idx.size} eligible markers < M_ELIGIBLE={m_eligible} (fail-closed; "
            f"no cell may contribute unequal marker support)")
    return idx[:m_eligible]
