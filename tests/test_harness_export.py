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


def test_operating_point_frozen():
    from critaudit.sim.harness import harness_spec as hs
    assert isinstance(hs.COUPLING_KNOB, str) and hs.COUPLING_KNOB
    op = hs.OPERATING_POINT
    for k in ("n_agents", "n_rounds", "network_density", "news_rate", "social_influence"):
        assert k in op
    assert op["n_agents"] >= 3


# --- harness_spec: NETWORK_CONSTRUCTION + NEWS_INJECTION consumed-guard (Phase B deferred freeze,
#     DECISIONS.md 2026-07-13 Ratification 2) — existence/range guards, not value pins ------------

def test_network_news_construction_frozen():
    from critaudit.sim.harness import harness_spec as hs
    # network axis: rule form + the named OASIS realization surface are frozen non-empty strings
    assert isinstance(hs.NETWORK_GRAPH_FORM, str) and hs.NETWORK_GRAPH_FORM
    assert isinstance(hs.NETWORK_EDGE_SURFACE, str) and hs.NETWORK_EDGE_SURFACE
    # seeding convention: namespaced spawn-key streams present, non-negative ints, all distinct
    # (graph draw and news draws must be independent streams — changing one cannot perturb another)
    streams = (hs.RNG_STREAM_GRAPH, hs.RNG_STREAM_NEWS_SCHEDULE, hs.RNG_STREAM_NEWS_CONTENT)
    assert all(isinstance(s, int) and s >= 0 for s in streams)
    assert len(set(streams)) == len(streams)
    # news axis: schedule form + author-identity rule frozen; the dedicated manual author sits
    # one past the last LLM-crowd id (graph has n_agents+1 members; n_agents stays the crowd count)
    assert isinstance(hs.NEWS_SCHEDULE_FORM, str) and hs.NEWS_SCHEDULE_FORM
    assert isinstance(hs.NEWS_AUTHOR_RULE, str) and hs.NEWS_AUTHOR_RULE
    assert hs.NEWS_USER_AGENT_ID == hs.OPERATING_POINT["n_agents"]
    # content pool: frozen tuple, auditable size, non-degenerate (content enters prompts and the
    # length_spread diagnostic — the pool alone must not be able to degenerate it)
    pool = hs.NEWS_POOL
    assert isinstance(pool, tuple)
    assert 8 <= len(pool) <= 16
    assert all(isinstance(s, str) and s.strip() for s in pool)
    assert len(set(pool)) == len(pool)                       # no duplicate strings
    lengths = [len(s) for s in pool]
    assert len(set(lengths)) == len(lengths)                 # all-distinct lengths
    assert float(np.std(lengths)) > hs.LENGTH_SPREAD_FLOOR   # pool spread clears the frozen floor


# --- harness_spec: Task-10 spec freezes consumed-guard (RECSYS_TYPE, MODEL_REVISION pin,
#     COHORT_MAX_TOKENS) — existence/range/drift guards, not value pins ---------------------------

def test_task10_spec_freezes_present_and_sane():
    import re
    from critaudit.sim.harness import harness_spec as hs
    # RECSYS_TYPE: frozen exact Platform-ctor value; must be a non-Reddit OASIS enum value
    # (Reddit mode skips the follow feed and breaks the round-granular pairing clock)
    assert hs.RECSYS_TYPE in ("twitter", "twhin-bert", "random")
    # MODEL_REVISION: pinned to a concrete 40-hex commit (no floating ref like "main")
    assert re.fullmatch(r"[0-9a-f]{40}", hs.MODEL_REVISION)
    # cross-file drift tripwire: modal_serve.py deliberately does NOT import harness_spec (and
    # `modal` is not importable under oasis_venv), so extract its SERVED_REVISION literal
    # textually and require it to equal the frozen pin — served substrate == registered pin.
    serve_path = os.path.join(os.path.dirname(__file__), "..", "src", "critaudit", "sim",
                              "harness", "modal_serve.py")
    with open(serve_path) as f:
        m = re.search(r'^SERVED_REVISION\s*=\s*"([0-9a-f]{40})"', f.read(), re.M)
    assert m, "SERVED_REVISION literal not found in modal_serve.py"
    assert m.group(1) == hs.MODEL_REVISION
    # COHORT_MAX_TOKENS: the COMPLETION CAP, decoupled from the context budget (owner-ratified
    # correction 2026-07-15 after the seed-1 context wall: CAMEL hardwires token_limit to
    # max_tokens, so the old 4096 served both roles and drove prompt+cap past the served 8192).
    # Anchored on the measured completion distribution; the owner's cap rule draws from an
    # enumerated menu, each >= 2x the observed max.
    assert isinstance(hs.COHORT_MAX_TOKENS, int)
    assert hs.COHORT_MAX_TOKENS in (512, 768, 1024)
    # COHORT_CONTEXT_BUDGET: the client-side context budget (ChatAgent memory trims to it via the
    # driver's token_limit override) — a positive multiple of 512, strictly above the cap, and the
    # necessary serving-cap inequality budget + cap + 256 declared slack <= 8192 (the measured
    # overhead term makes the frozen arithmetic stricter; recorded verbatim in the spec comment).
    assert isinstance(hs.COHORT_CONTEXT_BUDGET, int)
    assert hs.COHORT_CONTEXT_BUDGET > 0 and hs.COHORT_CONTEXT_BUDGET % 512 == 0
    assert hs.COHORT_CONTEXT_BUDGET > hs.COHORT_MAX_TOKENS
    assert hs.COHORT_CONTEXT_BUDGET + hs.COHORT_MAX_TOKENS + 256 <= 8192


# --- Task-10 PURE construction helpers (no OASIS import): the follow-edge builder and the news
#     schedule builder realizing the frozen NETWORK/NEWS rules. TDD'd here against the frozen
#     constants; run_oasis_minimal drives OASIS with exactly these two outputs. ------------------

def test_build_follow_edges_operating_point_count_and_shape():
    from critaudit.sim.harness.oasis_adapter import build_follow_edges
    from critaudit.sim.harness import harness_spec as hs
    n = hs.OPERATING_POINT["n_agents"]           # 50
    d = hs.OPERATING_POINT["network_density"]    # 0.10
    edges = build_follow_edges(hs.COHORT_SEEDS[0], n_agents=n, density=d)
    assert len(edges) == 245                      # round(0.10 * 50 * 49) — the frozen exact-count M
    assert all(u != v for u, v in edges)          # no self-loops (u != v; the n*(n-1) denominator)
    assert len(set(edges)) == len(edges)          # distinct ordered pairs (without replacement)
    assert all(0 <= u < n and 0 <= v < n for u, v in edges)   # crowd-only ids 0..n_agents-1
    assert all(isinstance(u, int) and isinstance(v, int) for u, v in edges)


def test_build_follow_edges_deterministic_and_distinct_across_seeds():
    from critaudit.sim.harness.oasis_adapter import build_follow_edges
    e0a = build_follow_edges(20260627, n_agents=50, density=0.10)
    e0b = build_follow_edges(20260627, n_agents=50, density=0.10)
    e1 = build_follow_edges(20260628, n_agents=50, density=0.10)
    assert e0a == e0b            # byte-determinism: pure function of the seed
    assert e0a != e1            # distinct across (consecutive) seeds


def test_build_follow_edges_stream_independent_of_news_consumption():
    # namespaced spawn-key streams: perturbing the news draws (any amount, any rate) must NOT
    # change the graph — the frozen decoupling that makes density a clean axis.
    from critaudit.sim.harness.oasis_adapter import build_follow_edges, build_news_schedule
    seed = 20260627
    before = build_follow_edges(seed, n_agents=50, density=0.10)
    build_news_schedule(seed, n_rounds=1000, news_rate=0.9)   # heavy schedule+content consumption
    build_news_schedule(seed, n_rounds=7, news_rate=0.3)
    after = build_follow_edges(seed, n_agents=50, density=0.10)
    assert before == after


def test_build_news_schedule_shape_range_and_determinism():
    from critaudit.sim.harness.oasis_adapter import build_news_schedule
    from critaudit.sim.harness import harness_spec as hs
    nr = hs.OPERATING_POINT["n_rounds"]          # 20
    rate = hs.OPERATING_POINT["news_rate"]       # 0.05
    s0a = build_news_schedule(hs.COHORT_SEEDS[0], n_rounds=nr, news_rate=rate)
    s0b = build_news_schedule(hs.COHORT_SEEDS[0], n_rounds=nr, news_rate=rate)
    assert len(s0a) == nr                         # one entry per round
    assert s0a == s0b                             # deterministic per seed
    # each entry is None (no inject) or an in-range NEWS_POOL string (pool index in range)
    assert all(x is None or x in hs.NEWS_POOL for x in s0a)


def test_build_news_schedule_rate_bounds_and_seed_variation():
    from critaudit.sim.harness.oasis_adapter import build_news_schedule
    from critaudit.sim.harness import harness_spec as hs
    all_on = build_news_schedule(hs.COHORT_SEEDS[0], n_rounds=20, news_rate=1.0)
    all_off = build_news_schedule(hs.COHORT_SEEDS[0], n_rounds=20, news_rate=0.0)
    assert all(x is not None and x in hs.NEWS_POOL for x in all_on)  # rate 1.0 -> every round injects
    assert all(x is None for x in all_off)                          # rate 0.0 -> none
    # the realized inject pattern varies across (consecutive) seeds at an intermediate rate
    a = [x is None for x in build_news_schedule(hs.COHORT_SEEDS[0], n_rounds=300, news_rate=0.5)]
    b = [x is None for x in build_news_schedule(hs.COHORT_SEEDS[1], n_rounds=300, news_rate=0.5)]
    assert a != b
