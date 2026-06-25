"""Driven mean-field Deffuant + activation-passing contagion — the classical-ABM control (Stage-2
artifact gate part 1). Emits a native labeled event stream (times, root_id, parent_idx) feeding the
shipped pipeline (gate / post_reply_tree / CSN / scaling), plus a belief trajectory (for χ) and
attempt/success bookkeeping (for the gate-independent structural branching ratio n_tree).

eps (Deffuant confidence bound) tunes the offspring COUNT (m = K_REACH·P(|Δx|<eps)); a FROZEN
Lomax(KERNEL_EPS, KERNEL_C) kernel sets the offspring TIMING (matched to the gate's calibration regime).
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


def _pair_update(opinions, a, b, mu_step):
    """Symmetric Deffuant step: a and b each move toward the other by mu_step·gap. Both deltas are
    computed from the PRE-update values, then applied — an in-place sequential write (b's update
    reading a's already-moved value) silently breaks the midpoint/symmetry invariant. Mutates in place."""
    xa, xb = opinions[a], opinions[b]
    opinions[a] = xa + mu_step * (xb - xa)
    opinions[b] = xb + mu_step * (xa - xb)


def _grow_tree(opinions, root_agent, news_time, eps, k_reach, mu_step, kernel_eps, c, horizon, rng):
    """One activation-passing contagion tree (mean-field). The root fires at news_time; each firing
    agent makes k_reach attempts on uniform-random partners. A confidence-compatible attempt
    (|Δopinion| < eps) is a SUCCESS: it moves both opinions (Deffuant) and counts toward the
    generative branching ratio. If the partner is still susceptible IN THIS TREE it activates →
    a new offspring event at parent_time + Lomax(kernel_eps, c) delay; if already activated, the
    success is a COLLISION (counted, no new node → bounds supercritical cascades at the population).
    One firing per agent per tree.

    FINITE OBSERVATION WINDOW: an offspring whose firing time would land at/after `horizon` is CENSORED
    — the same `ct < horizon` gate the reference generators.powerlaw_hawkes applies to every child
    (line 89). No real crowd is observed over an infinite window, and with the frozen infinite-mean
    Lomax kernel an uncensored supercritical cascade smears arbitrarily far past the drive, so the gate
    would be fitted on an out-of-calibration horizon. The SUCCESS/opinion-update still counts (the
    interaction happens at the parent's in-window firing), but a censored offspring is NOT marked
    refractory — only an OBSERVED (in-window) firing activates the agent. This matches the reference's
    "only in-window events have effects" semantics and prevents a censored FUTURE activation from
    suppressing an earlier in-window one (an undercount, biased toward reading subcritical, that the
    2nd-pass review caught). n_tree stays a local per-firing ratio (preserved under truncation) and the
    stream is bounded to [0, horizon). Same generation-order queue as the reference (NOT chronological —
    keeping it identical to the process the gate is calibrated on). Mutates `opinions`."""
    n = opinions.size
    times = [float(news_time)]
    agents = [int(root_agent)]
    parents_local = [-1]
    activated = {int(root_agent)}
    queue = [0]
    successes = 0
    while queue:
        e = queue.pop()
        ag = agents[e]
        for b in rng.integers(0, n, size=k_reach):
            b = int(b)
            if b == ag:
                continue
            if abs(opinions[ag] - opinions[b]) < eps:        # bounded-confidence success
                successes += 1                               # generative branching count (collisions incl.)
                _pair_update(opinions, ag, b, mu_step)
                if b not in activated:                       # still susceptible in this tree
                    u = float(rng.uniform(0.0, 1.0))
                    d = c * ((1.0 - u) ** (-1.0 / kernel_eps) - 1.0)   # Lomax(kernel_eps, c) delay > 0
                    ct = times[e] + d
                    if ct < horizon:                         # in-window firing → offspring event
                        activated.add(b)                     # only an OBSERVED firing makes b refractory
                        times.append(ct)
                        agents.append(b)
                        parents_local.append(e)
                        queue.append(len(times) - 1)
                    # else: fires out-of-window — censored (no node, no in-window descendants)
    return times, agents, parents_local, successes


@dataclass
class AbmRun:
    times: np.ndarray          # sorted event times
    root_id: np.ndarray        # int64; each event's cascade root (sorted index); immigrant = own index
    parent_idx: np.ndarray     # int64; parent event (sorted index), -1 for immigrants; parent_idx[i] < i
    belief_traj: np.ndarray    # mean opinion sampled after each tree (news-time order) — for χ
    successes: int             # total confidence-compatible attempts (collisions incl.) — for n_tree


def simulate_labeled(eps, horizon, mu_news, *, N, k_reach, mu_step, kernel_eps, c, rng,
                     max_events=500_000):
    """Driven mean-field Deffuant + activation-passing contagion. News (Poisson rate mu_news) shocks a
    random agent (re-randomizing its opinion to maintain spread against convergence) → a root event;
    its contagion tree grows via `_grow_tree`. Events are pooled across trees, then time-sorted and
    relabeled into sorted-index space (mirrors generators.powerlaw_hawkes.simulate_labeled). Opinions
    persist and evolve across trees (the slow opinion dynamics → belief_traj/χ)."""
    if rng is None:
        raise ValueError("pass an explicit numpy Generator as rng")
    opinions = rng.uniform(0.0, 1.0, size=N)
    n_imm = int(rng.poisson(mu_news * horizon))
    news_times = np.sort(rng.uniform(0.0, horizon, size=n_imm))
    times, parents, roots = [], [], []
    belief_traj = np.empty(n_imm)
    successes = 0
    for r in range(n_imm):
        root_agent = int(rng.integers(0, N))
        opinions[root_agent] = float(rng.uniform(0.0, 1.0))     # news re-randomizes the shocked agent
        base = len(times)
        t_tree, _ag_tree, par_tree, succ = _grow_tree(opinions, root_agent, float(news_times[r]),
                                                      eps, k_reach, mu_step, kernel_eps, c, horizon, rng)
        successes += succ
        for j in range(len(t_tree)):
            times.append(t_tree[j])
            parents.append(-1 if par_tree[j] < 0 else base + par_tree[j])   # gen-index space
            roots.append(base)                                              # tree root's gen-index
        belief_traj[r] = float(opinions.mean())
        if len(times) > max_events:
            raise RuntimeError("event explosion — lower mu_news/eps or the per-plant event budget")
    t = np.asarray(times, dtype=float)
    if t.size == 0:
        empty = np.empty(0, dtype=np.int64)
        return AbmRun(times=t, root_id=empty, parent_idx=empty, belief_traj=belief_traj, successes=0)
    order = np.argsort(t, kind="stable")                        # gen-order → time-sorted
    inv = np.empty(t.size, dtype=np.int64)
    inv[order] = np.arange(t.size)
    pg = np.asarray(parents, dtype=np.int64)[order]
    parent_sorted = np.where(pg < 0, -1, inv[np.where(pg < 0, 0, pg)])
    root_sorted = inv[np.asarray(roots, dtype=np.int64)[order]]
    return AbmRun(times=t[order], root_id=root_sorted, parent_idx=parent_sorted,
                  belief_traj=belief_traj, successes=successes)
