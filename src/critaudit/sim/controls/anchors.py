"""Gate-INDEPENDENT anchors for the shakedown plants.

n_tree (PRIMARY) — the structural branching ratio counted from the generator's OWN bookkeeping
(successful confidence-compatible attempts per firing). Monotonic in eps by construction
(P(|Δx|<eps) ↑ eps) and crosses 1, so it ORDERS the LOW/HIGH plants across criticality. The
shakedown then tests whether the gate's FITTED n̂ recovers this planted n_tree — an independent
check (direct count of ground truth vs Hawkes inference), never circular: n_tree NEVER reads
post_reply_tree's reconstruction (the same pure-relay fence as cascades.ground_truth).

chi (SECONDARY) — variance of the aggregate-belief trajectory, intended as a consensus susceptibility.
A *true* susceptibility is non-monotonic in eps (peaks at criticality) and so could only LOCATE the
critical point, never ORDER sub vs super — which already disqualifies it as the plant certifier. The
shakedown then MEASURED that this var(population-mean) proxy does not even locate it: the population
mean is ~0.5 by the symmetric dynamics, so it is not an order parameter and its temporal variance is
flat-to-noisy in eps, not peaked at eps_crit (see the 2026-06-24 increment-3 DECISIONS entry +
results/2026-06-24_chi_diagnostic.py). χ is therefore corroboration-only, and a future sweep needing a
locator must redefine it (e.g. cross-agent opinion dispersion), not use var(population-mean).
"""
from __future__ import annotations
import numpy as np


def n_tree(run):
    """Generative branching ratio = mean successful attempts per firing event (collisions included).
    From AbmRun bookkeeping ONLY (run.successes / run.times.size). Monotonic in eps; crosses 1."""
    if run.times.size == 0:
        raise ValueError("n_tree needs >= 1 event")
    return float(run.successes) / float(run.times.size)


def chi(run):
    """Consensus susceptibility = variance of the aggregate-belief trajectory (secondary observable)."""
    if run.belief_traj.size == 0:
        return float("nan")
    return float(np.var(run.belief_traj))
