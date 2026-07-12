from __future__ import annotations
import json
import sqlite3
from critaudit.sim.harness.types import EventRecord, RefreshRecord
from critaudit.sim.harness.assemble import assemble_harness_run


# The emit actions OASIS logs to `trace`, and the info key naming the content id each one CREATED.
# Confirmed against the OASIS source (oasis/social_platform/platform.py, recon 2026-06-30):
#   create_post    -> {"content", "post_id"}                 (post_id)
#   quote_post     -> {"quoted_id", "new_post_id"}           (new_post_id)
#   repost         -> {"reposted_id", "new_post_id"}         (new_post_id)
#   create_comment -> {"content", "comment_id"}              (comment_id)
# Each created id maps into the SAME item_id namespace used for EventRecords ('post:<id>' /
# 'comment:<id>'), so the emit's trace rowid can be joined onto its event as the `seq` tiebreaker.
_EMIT_ID_KEY = {
    "create_post": ("post", "post_id"),
    "quote_post": ("post", "new_post_id"),
    "repost": ("post", "new_post_id"),
    "create_comment": ("comment", "comment_id"),
}


def _served_post_ids(info):
    """Extract served post ids from a REFRESH trace's `info` (JSON string or already-parsed dict).
    Confirmed shape (Task 1): {"posts": [{"post_id": <id>, ...}, ...]}. FAIL-CLOSED on a shape that
    does not match (so a schema drift is a loud error, not a silent empty served set)."""
    d = json.loads(info) if isinstance(info, str) else info
    posts = d.get("posts")
    if posts is None:
        raise ValueError("REFRESH info has no 'posts' key — schema drift; re-run Task-1 recon")
    return [p["post_id"] for p in posts]


def _emit_item_id(action, info):
    """The item_id an EMIT trace row created (e.g. 'post:4' / 'comment:3'), used to join the row's
    rowid onto the matching event as its `seq`. Returns None for a non-emit action (nothing to join).
    FAIL-CLOSED: an emit action whose `info` lacks its confirmed id key is schema drift and raises
    (so a broken join surfaces loudly, never as a silent seq=0)."""
    ns_key = _EMIT_ID_KEY.get(action)
    if ns_key is None:
        return None
    ns, key = ns_key
    d = json.loads(info) if isinstance(info, str) else info
    if key not in d:
        raise ValueError(f"{action} trace info lacks {key!r} — schema drift; re-run Task-1 recon")
    return f"{ns}:{d[key]}"


def _event_seq(item_id, parent_item_id, seq_by_item):
    """The event's `seq` = the rowid of its OWN emit trace row (the counter shared with refreshes).
    STRICT join: an emit WITH a parent must have a trace row (every emit-with-parent joins cleanly on
    the real recon trace, 2026-06-30) — a missing one raises rather than defaulting seq=0, which would
    silently mis-order a same-round read->emit pair. A parentless root never enters pairing, so a
    missing trace row there is harmless (seq=0)."""
    seq = seq_by_item.get(item_id)
    if seq is not None:
        return seq
    if parent_item_id is not None:
        raise ValueError(
            f"emit {item_id!r} (parent {parent_item_id!r}) has no trace row — cannot place it in the "
            f"read->emit (created_at, rowid) ordering; un-traced emit or schema drift")
    return 0


def export_harness_run(db_path, *, timestamp_col):
    """Read the OASIS post/comment/trace tables into the normalized HarnessRun. `timestamp_col` is the
    confirmed time column ('created_at' per the Task-1 recon). The DB is opened READ-ONLY so a source
    trace (e.g. the committed recon fixture) can never be mutated.

    Two passes over the data:
      1. `trace` -> REFRESH records (seq = trace rowid) AND an item_id -> trace rowid map for every
         emit action (the seq-join source).
      2. `post`/`comment` -> EventRecords, each carrying seq from its OWN emit trace row so refresh-seq
         and emit-seq share the one counter the round-granular read->emit tiebreaker needs.
    Fail-closed throughout: `_served_post_ids`/`_emit_item_id` raise on info-shape drift, the strict
    seq-join raises on an un-traced emit-with-parent, and `assemble_harness_run`'s `build_parent_root`
    raises on an unresolvable/duplicate/out-of-order parent (surfaced, not swallowed)."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        # Pass 1: trace -> refreshes + emit(item_id) -> rowid. rowid is trace insertion order.
        refreshes = []
        seq_by_item = {}
        for rowid, uid, ts, action, info in con.execute(
                f"SELECT rowid, user_id, {timestamp_col}, action, info FROM trace ORDER BY rowid"):
            if action == "refresh":
                served = frozenset(f"post:{pid}" for pid in _served_post_ids(info))
                refreshes.append(RefreshRecord(int(uid), float(ts), served, seq=int(rowid)))
                continue
            item = _emit_item_id(action, info)
            if item is None:
                continue
            if item in seq_by_item:
                raise ValueError(f"duplicate emit trace for {item!r} (rowid {rowid}) — schema drift")
            seq_by_item[item] = int(rowid)

        # Pass 2: content rows -> events (posts before comments keeps parents before children on ties).
        events = []
        for pid, uid, orig, content, ts in con.execute(
                f"SELECT post_id, user_id, original_post_id, content, {timestamp_col} "
                f"FROM post ORDER BY post_id"):
            item_id = f"post:{pid}"
            parent = f"post:{orig}" if orig is not None else None      # NULL original_post_id = root
            events.append(EventRecord(item_id, float(ts), int(uid), parent, content or "",
                                      seq=_event_seq(item_id, parent, seq_by_item)))
        for cid, pid, uid, content, ts in con.execute(
                f"SELECT comment_id, post_id, user_id, content, {timestamp_col} "
                f"FROM comment ORDER BY comment_id"):
            item_id = f"comment:{cid}"
            parent = f"post:{pid}"                                     # a comment's parent is its post
            events.append(EventRecord(item_id, float(ts), int(uid), parent, content or "",
                                      seq=_event_seq(item_id, parent, seq_by_item)))
    finally:
        con.close()
    return assemble_harness_run(events, refreshes)
