import json
import os
import sqlite3

import numpy as np
from critaudit.sim.harness.types import EventRecord, RefreshRecord
from critaudit.sim.harness.assemble import build_parent_root, assemble_harness_run
from critaudit.sim.controls.anchors import read_emit_ratio, n_struct
from critaudit.cascades.extract import post_reply_tree
from critaudit.sim.harness.oasis_adapter import export_harness_run


def _events():
    # two trees: p0<-c1<-c2 (root 0), and a lone p3
    return [
        EventRecord("p0", 0.0, 0, None, "root a"),
        EventRecord("c1", 1.0, 1, "p0", "reply to p0"),
        EventRecord("p3", 1.5, 0, None, "root b"),
        EventRecord("c2", 2.0, 2, "c1", "reply to c1"),
    ]


def test_build_parent_root_shapes_and_invariants():
    times, root_id, parent_idx = build_parent_root(_events())
    assert np.allclose(times, [0.0, 1.0, 1.5, 2.0])
    assert parent_idx.tolist() == [-1, 0, -1, 1]
    assert root_id.tolist() == [0, 0, 2, 0]
    # feeds post_reply_tree without raising; sizes/durations as expected
    av = post_reply_tree(times, root_id, parent_idx)
    assert sorted(av.sizes.tolist()) == [1, 3]
    assert sorted(av.durations.tolist()) == [1, 3]


def test_build_parent_root_unknown_parent_raises():
    bad = [EventRecord("c0", 0.0, 0, "missing", "x")]
    try:
        build_parent_root(bad)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_assemble_and_read_emit_ratio_below_n_struct():
    events = _events()  # 4 events, 2 roots -> n_struct = 1 - 2/4 = 0.5
    refreshes = [RefreshRecord(1, 0.5, frozenset({"p0"}))]  # only c1 is a read->emit success
    run = assemble_harness_run(events, refreshes)
    assert run.times.size == 4
    assert run.content == ["root a", "reply to p0", "root b", "reply to c1"]
    av = post_reply_tree(run.times, run.root_id, run.parent_idx)
    assert sorted(av.sizes.tolist()) == [1, 3]
    assert read_emit_ratio(run) == 0.25
    assert read_emit_ratio(run) <= n_struct(av)      # the load-bearing inequality (accessibility, not crosses-1)


def test_read_emit_ratio_empty_raises():
    import numpy as np
    from critaudit.sim.harness.types import HarnessRun
    empty = HarnessRun(np.array([]), np.array([], np.int64), np.array([], np.int64),
                       np.array([], bool), [])
    try:
        read_emit_ratio(empty)
        assert False, "expected ValueError"
    except ValueError:
        pass


# --- export_harness_run: OASIS SQLite -> HarnessRun (Task 5) -----------------------------------
# Schema is the CONFIRMED OASIS one (recon 2026-06-30): trace(user_id, created_at, action, info) —
# JSON column 'info', timestamp 'created_at', refresh action 'refresh'. Emit trace rows carry the
# created content id in info (create_post->post_id, create_comment->comment_id, quote/repost->
# new_post_id, all source-confirmed in oasis/social_platform/platform.py), so an emit's trace rowid
# (its seq) shares the same counter as a refresh's rowid — the within-round read->emit tiebreaker.

def _build_synthetic_oasis_db(path):
    """Synthetic OASIS DB on the CONFIRMED schema, covering the comment->post parent path (the real
    fixture's emits are all quote_posts, so comments are only exercised here). Round-granular clock:
    round 0 creates two root posts; round 1 refreshes then emits two comments that SHARE created_at
    with the refresh, so the read->emit pair reconstructs ONLY via the trace-rowid seq join (a bare
    created_at compare would reconstruct 0). All parents resolve to an existing post."""
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE post(post_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INT,
                          original_post_id INT, content TEXT, created_at REAL);
        CREATE TABLE comment(comment_id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INT,
                             user_id INT, content TEXT, created_at REAL);
        CREATE TABLE trace(user_id INT, created_at REAL, action TEXT, info TEXT);
        """
    )
    # round 0: two ORIGINAL posts (original_post_id NULL = root)
    con.execute("INSERT INTO post VALUES(1, 1, NULL, 'root a', 0.0)")
    con.execute("INSERT INTO post VALUES(2, 2, NULL, 'root b', 0.0)")
    # round 1: two comments, both replying to post 1 (a comment's parent is a POST -> post:1)
    con.execute("INSERT INTO comment VALUES(1, 1, 1, 'reply by u1', 1.0)")
    con.execute("INSERT INTO comment VALUES(2, 1, 2, 'reply by u2', 1.0)")
    # trace rows: rowid = insertion order = the seq counter shared by refreshes and emits.
    con.execute("INSERT INTO trace VALUES(1, 0.0, 'create_post', ?)",
                (json.dumps({"content": "root a", "post_id": 1}),))           # rowid 1 -> post:1
    con.execute("INSERT INTO trace VALUES(2, 0.0, 'create_post', ?)",
                (json.dumps({"content": "root b", "post_id": 2}),))           # rowid 2 -> post:2
    con.execute("INSERT INTO trace VALUES(1, 1.0, 'refresh', ?)",
                (json.dumps({"posts": [{"post_id": 1}, {"post_id": 2}]}),))   # rowid 3 (u1 read)
    con.execute("INSERT INTO trace VALUES(1, 1.0, 'create_comment', ?)",
                (json.dumps({"content": "reply by u1", "comment_id": 1}),))   # rowid 4 -> comment:1
    con.execute("INSERT INTO trace VALUES(2, 1.0, 'create_comment', ?)",
                (json.dumps({"content": "reply by u2", "comment_id": 2}),))   # rowid 5 -> comment:2
    con.commit()
    con.close()


def test_export_harness_run_from_synthetic_db(tmp_path):
    db = str(tmp_path / "oasis.db")
    _build_synthetic_oasis_db(db)
    run = export_harness_run(db, timestamp_col="created_at")
    # 4 events: 2 root posts + 2 comments.
    assert run.times.size == 4
    assert run.content == ["root a", "root b", "reply by u1", "reply by u2"]
    # tree: post1 <- {comment1, comment2} (size 3) and the lone post2 (size 1).
    av = post_reply_tree(run.times, run.root_id, run.parent_idx)
    assert sorted(av.sizes.tolist()) == [1, 3]
    # read->emit: only u1's comment reconstructs — u1's refresh (rowid 3) precedes its same-created_at
    # comment (rowid 4) via the seq join; u2 never refreshed. If the seq join were absent (seq=0), the
    # same-round pair would NOT reconstruct, so this asserts the join end-to-end.
    assert int(run.read_emit_success.sum()) == 1
    assert read_emit_ratio(run) == 0.25
    assert read_emit_ratio(run) <= n_struct(av)   # accessibility is a subset of realized edges


_REAL_TRACE = os.path.join(os.path.dirname(__file__), "fixtures", "oasis_trace_recon.sqlite")


def test_export_harness_run_real_trace_regression():
    """REGRESSION ANCHOR — the Task-1 recon banked, on THIS exact fixture (DECISIONS 2026-06-30):
    7 events (3 root posts + 3 LLM quote_posts + 1 manual repost), A3 = 3 same-round read->emit pairs
    (cross-round false-pairs = 0), B = 4 repost/quote->original parent links. These are banked facts,
    NOT targets to tune toward: a mismatch is a finding for the controller, never a reason to adjust
    the join/pairing/parser."""
    run = export_harness_run(_REAL_TRACE, timestamp_col="created_at")
    assert run.times.size == 7                                   # 3 roots + 3 quotes + 1 repost
    assert int((run.parent_idx >= 0).sum()) == 4                 # B: 4 quote/repost -> original links
    assert int((run.parent_idx < 0).sum()) == 3                  # 3 original (root) posts
    assert int(run.read_emit_success.sum()) == 3                 # A3: 3 same-round read->emit pairs
    assert read_emit_ratio(run) == 3 / 7


# --- harness_spec: FROZEN result-blind surface consumed-guard (Task 6) --------------------------

def test_harness_spec_frozen_constants_present_and_sane():
    from critaudit.sim.harness import harness_spec as hs
    assert 0.0 < hs.READ_EMIT_FLOOR < 1.0
    assert 0.0 < hs.MAX_FRAC_SIZE1 <= 1.0
    assert 0.0 < hs.MAX_GIANT_FRAC <= 1.0
    assert hs.LENGTH_SPREAD_FLOOR > 0.0
    assert isinstance(hs.MODEL_ID, str) and hs.MODEL_ID
    assert isinstance(hs.MODEL_REVISION, str) and hs.MODEL_REVISION
    assert len(hs.COHORT_SEEDS) >= 3
