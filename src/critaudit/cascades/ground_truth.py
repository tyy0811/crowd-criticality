"""Gate-D cascade GROUND TRUTH — a PURE PACKAGER of the generator's mechanical parent->offspring tree.
It calls simulate_labeled and relays its native (root_id, parent_idx) as the scored-against truth, and
contains NO cascade-definition logic of its own. The truth is the generator's tree, untouched, so the
recovery test is non-circular: the extractor must rediscover this truth from LESS information (#1 from
parent links, #3 from timing only). DO NOT add segmentation/assignment logic in this file."""
from __future__ import annotations
import numpy as np
from critaudit.generators.powerlaw_hawkes import simulate_labeled


def labeled_stream(n, horizon, mu, eps, c, rng, max_events=500_000):
    """(times, is_belief_update, root_id, parent_idx). is_belief_update is all-True in the synthetic
    (every event is a candidate — the flag is the real/sim interface); root_id is the TRUE cascade
    membership relayed verbatim from simulate_labeled (NOT recomputed here)."""
    times, root_id, parent_idx = simulate_labeled(n, horizon, mu, eps, c, rng, max_events)
    is_belief_update = np.ones(times.size, dtype=bool)
    return times, is_belief_update, root_id, parent_idx
