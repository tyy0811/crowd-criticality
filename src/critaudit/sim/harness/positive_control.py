"""Harness positive control (design §8): is the reference crowd GENUINELY coupled, or degenerate?
Fail-closed — raises and blocks interpretation, mirroring the parrot-null §6 gate. Validates ONLY
read->emit accessibility + coupling presence; makes NO crosses-1 regime claim (design §2/§12)."""
from __future__ import annotations
import numpy as np
from critaudit.cascades.extract import post_reply_tree
from critaudit.sim.controls.anchors import read_emit_ratio
from critaudit.sim.harness import harness_spec as hs


def check_positive_control(run):
    av = post_reply_tree(run.times, run.root_id, run.parent_idx)
    sizes = av.sizes
    n_events = int(sizes.sum())
    frac_size1 = float((sizes == 1).sum()) / sizes.size
    giant_frac = float(sizes.max()) / n_events
    rer = read_emit_ratio(run)
    lengths = np.array([len(c) for c in run.content], dtype=float)
    length_spread = float(lengths.std())
    diag = {"frac_size1": frac_size1, "giant_frac": giant_frac,
            "read_emit_ratio": rer, "length_spread": length_spread}
    ok = (frac_size1 <= hs.MAX_FRAC_SIZE1 and giant_frac <= hs.MAX_GIANT_FRAC
          and rer > hs.READ_EMIT_FLOOR and length_spread > hs.LENGTH_SPREAD_FLOOR)
    if not ok:
        raise AssertionError(f"positive control failed (degenerate reference): {diag} "
                             f"vs thresholds frac_size1<={hs.MAX_FRAC_SIZE1}, giant<={hs.MAX_GIANT_FRAC}, "
                             f"read_emit>{hs.READ_EMIT_FLOOR}, length_spread>{hs.LENGTH_SPREAD_FLOOR} (design §8)")
    return diag
