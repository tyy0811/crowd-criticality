from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class EventRecord:
    """One emitted content item, normalized from OASIS. item_id is unique across the run
    (e.g. 'post:5' / 'comment:3'); parent_item_id is the item this responds to (None = originating
    post = a root). Provide records in causal insertion order (so a stable time-sort keeps
    parent-before-child on equal timestamps). seq = trace insertion-order (rowid): the WITHIN-round
    tiebreaker used by read->emit pairing when a same-round refresh and emit share `time` (OASIS's
    clock is round-granular); it never orders across rounds (time is primary). Default 0 = no
    within-round tie to break (distinct timestamps)."""
    item_id: str
    time: float
    agent_id: int
    parent_item_id: str | None
    content: str
    seq: int = 0


@dataclass(frozen=True)
class RefreshRecord:
    """One REFRESH (read): the set of item_ids served to agent_id at time. seq = trace insertion-order
    (rowid), the within-round tiebreaker (see EventRecord.seq); default 0."""
    agent_id: int
    time: float
    served_item_ids: frozenset
    seq: int = 0


@dataclass
class HarnessRun:
    """Normalized harness output — mirrors AbmRun's consumed fields (times/root_id/parent_idx,
    time-sorted, sorted-index space, parent_idx[i] < i, immigrant = own root_id) so post_reply_tree
    and anchors consume it unchanged. read_emit_success: per-event bool. content: per-event text."""
    times: np.ndarray
    root_id: np.ndarray
    parent_idx: np.ndarray
    read_emit_success: np.ndarray
    content: list
