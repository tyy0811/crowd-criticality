"""Pure observable computation for HarnessRun (parrot-v2, spec rev-5 §4).
The SAME quantities the positive control computes, WITHOUT any threshold gate —
v2 code must never invoke check_positive_control (it asserts coupling)."""
import numpy as np
from critaudit.cascades.extract import post_reply_tree
from critaudit.sim.controls.anchors import read_emit_ratio


def compute_observables(run) -> dict:
    if run.times.size == 0:
        raise ValueError("compute_observables: empty run (fail-closed)")
    av = post_reply_tree(run.times, run.root_id, run.parent_idx)
    sizes = av.sizes
    n_events = int(sizes.sum())
    lengths = np.array([len(c) for c in run.content], dtype=float)
    return {
        "n_events": n_events,
        "frac_size1": float((sizes == 1).sum()) / sizes.size,
        "giant_frac": float(sizes.max()) / n_events,
        "length_spread": float(lengths.std()),
        "read_emit_ratio": read_emit_ratio(run),
    }


GATED_OBSERVABLES = ("n_events", "frac_size1", "giant_frac", "length_spread")
# read_emit_ratio is DESCRIPTIVE (exposure diagnostic) — never part of equality.
