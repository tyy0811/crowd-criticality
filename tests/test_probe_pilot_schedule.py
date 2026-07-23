"""Fast tests for the sub-inc-3 pilot machinery (T10): the frozen deterministic schedule, the
resolve_schedule default-path equivalence (the keyword-only extension must be byte-equivalent to
pre-extension behavior when schedule=None), and the exposure/tree accounting verified against the
known synthetic DB (the metric-sanity pre-flight analog). The paid pilot run itself is NOT in CI."""
import sqlite3

import pytest

from critaudit.experiments.probe_pilot_oasis import (
    build_probe_schedule, count_exposures, marker_post_ids, marker_tree_size)
from critaudit.sim.controls import probe_spec as pspec
from critaudit.sim.harness import harness_spec as hs
from critaudit.sim.harness.oasis_adapter import build_news_schedule, resolve_schedule
# Sibling test module imported TOP-LEVEL (no `tests.` prefix): pytest's prepend import-mode puts
# tests/ itself on sys.path in every invocation, whereas the `tests.` package form only resolved
# locally by the accident of `python -m pytest` from the repo root (CI runs bare `pytest` — the
# PR #11 collection failure, 2026-07-21).
from test_harness_export import _build_synthetic_oasis_db


def test_probe_schedule_deterministic_and_frozen():
    s1, s2 = build_probe_schedule(), build_probe_schedule()
    assert s1 == s2
    assert len(s1) == hs.OPERATING_POINT["n_rounds"]
    injected = {r: c for r, c in enumerate(s1) if c is not None}
    assert tuple(injected) == pspec.PILOT_INJECTION_ROUNDS
    assert list(injected.values()) == [hs.NEWS_POOL[k] for k in pspec.PILOT_MARKER_POOL_INDICES]
    assert len(set(injected.values())) == 5                  # distinct markers -> unambiguous


def test_resolve_schedule_default_path_equivalence():
    # schedule=None must reproduce the pre-extension behavior EXACTLY (build_news_schedule on
    # the same seed/operating point) — the tripwire that the extension cannot perturb sub-inc-1
    # semantics.
    op = hs.OPERATING_POINT
    assert resolve_schedule(20260627, op, None) == build_news_schedule(
        20260627, n_rounds=op["n_rounds"], news_rate=op["news_rate"])


def test_resolve_schedule_explicit_passthrough_and_fail_closed():
    op = hs.OPERATING_POINT
    sched = build_probe_schedule()
    assert resolve_schedule(1, op, sched) == sched           # verbatim passthrough
    with pytest.raises(ValueError, match="length"):
        resolve_schedule(1, op, sched[:-1])
    bad = list(sched)
    bad[0] = 123
    with pytest.raises(ValueError, match="neither None nor str"):
        resolve_schedule(1, op, bad)


def test_exposure_and_tree_accounting_on_known_db(tmp_path):
    # Metric sanity on the KNOWN synthetic DB: refresh rowid 3 served posts {1, 2}; trees are
    # post1<-{comment1, comment2, repost4} (size 4), post2<-quote3 (size 2), lone post5 (size 1).
    db = str(tmp_path / "oasis.db")
    _build_synthetic_oasis_db(db)
    exp = count_exposures(db, [1, 2, 5])
    assert exp == {1: 1, 2: 1, 5: 0}
    assert marker_tree_size(db, 1) == 4
    assert marker_tree_size(db, 2) == 2
    assert marker_tree_size(db, 5) == 1
    # marker_post_ids fail-closed: the synthetic DB has no news-user markers.
    with pytest.raises(ValueError, match="fail-closed"):
        marker_post_ids(db)


# --- Task 4: run_oasis_minimal fixed-frame causal hooks (fast; no OASIS import) ---------------
# The hooks must stay inert by default and fail closed BEFORE any model/platform work.

def _hook_frame(frame_id="frame:hooks"):
    from critaudit.sim.harness.causal_probe_records import (
        CandidatePair, ParentEligibility, SamplingFrame)
    return SamplingFrame(
        frame_id=frame_id,
        parent_records=(
            ParentEligibility("post:1", author_agent_id=10, created_round=0),
            ParentEligibility("post:2", author_agent_id=11, created_round=0),
        ),
        excluded_recipient_agent_ids=(10, 11, 99),
        candidate_pairs=(
            CandidatePair(
                pair_id="pair:1", parent_item_id="post:1", agent_id=20, round_id=1,
                stratum_id="agent:20:round:1", selection_probability=0.4,
                treatment_probability=0.5, parent_first_readable_round=1,
                prior_exposure_count=0, complete_same_action_opportunity=True),
            CandidatePair(
                pair_id="pair:2", parent_item_id="post:2", agent_id=20, round_id=1,
                stratum_id="agent:20:round:1", selection_probability=0.4,
                treatment_probability=0.5, parent_first_readable_round=1,
                prior_exposure_count=0, complete_same_action_opportunity=True),
        ),
    )


def _hook_controller(frame):
    from critaudit.sim.harness.causal_refresh import CausalRefreshController

    class _Stream:
        def random(self):
            return 0.99

    return CausalRefreshController(
        frame, _Stream(), _Stream(),
        parent_posts={"post:1": {"post_id": 1, "user_id": 10},
                      "post:2": {"post_id": 2, "user_id": 11}},
        filler_posts={"post:1": {"post_id": 3, "user_id": 12},
                      "post:2": {"post_id": 4, "user_id": 12}},
    )


def test_run_oasis_minimal_causal_hooks_default_inert():
    import inspect
    from critaudit.sim.harness.oasis_adapter import run_oasis_minimal
    parameters = inspect.signature(run_oasis_minimal).parameters
    for name in ("causal_frame", "causal_controller"):
        assert name in parameters
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters[name].default is None


def test_causal_hooks_must_be_supplied_together():
    from critaudit.sim.harness.oasis_adapter import run_oasis_minimal
    frame = _hook_frame()
    with pytest.raises(ValueError, match="together"):
        run_oasis_minimal(1, hs.OPERATING_POINT, "m", "http://invalid", "t",
                          causal_frame=frame)
    with pytest.raises(ValueError, match="together"):
        run_oasis_minimal(1, hs.OPERATING_POINT, "m", "http://invalid", "t",
                          causal_controller=_hook_controller(frame))


def test_causal_hooks_reject_non_identical_frame():
    from critaudit.sim.harness.oasis_adapter import run_oasis_minimal
    controller = _hook_controller(_hook_frame("frame:other"))
    with pytest.raises(ValueError, match="byte-identical"):
        run_oasis_minimal(1, hs.OPERATING_POINT, "m", "http://invalid", "t",
                          causal_frame=_hook_frame(), causal_controller=controller)


def test_causal_hooks_fail_closed_without_predraw_database(monkeypatch, tmp_path):
    from critaudit.sim.harness.oasis_adapter import run_oasis_minimal
    monkeypatch.setenv("HARNESS_COHORT_DIR", str(tmp_path))
    frame = _hook_frame()
    with pytest.raises(ValueError, match="database|trace"):
        run_oasis_minimal(1, hs.OPERATING_POINT, "m", "http://invalid", "t",
                          causal_frame=frame, causal_controller=_hook_controller(frame))


def test_eligibility_evidence_measures_complete_same_action_opportunity(tmp_path):
    """Opportunity is MEASURED, not assumed (review): recipient signed up AND
    the parent is a ROOT post — a derived (quote) parent cannot natively
    receive all three registered same-actions on the installed platform."""
    from critaudit.sim.harness.causal_probe_records import (
        CandidatePair, ParentEligibility, SamplingFrame)
    from critaudit.sim.harness.causal_probe_validation import (
        validate_frame_provenance)
    from critaudit.sim.harness.oasis_adapter import (
        NEWS_AGENT_NAME, load_frame_eligibility_evidence)

    db = str(tmp_path / "evidence.db")
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE user (user_id INTEGER PRIMARY KEY, agent_id INTEGER,
                           user_name TEXT, name TEXT);
        CREATE TABLE post (post_id INTEGER PRIMARY KEY, user_id INTEGER,
                           original_post_id INTEGER, content TEXT,
                           quote_content TEXT, created_at DATETIME);
        CREATE TABLE trace (user_id INTEGER, created_at DATETIME,
                            action TEXT, info TEXT);
        """
    )
    for agent_id, name in ((0, "author_a"), (1, "author_b"),
                           (2, "recipient"), (9, NEWS_AGENT_NAME)):
        con.execute("INSERT INTO user VALUES(?,?,?,?)",
                    (agent_id, agent_id, name, name))
    con.execute("INSERT INTO post VALUES(1, 0, NULL, 'root parent', NULL, 0)")
    con.execute("INSERT INTO post VALUES(2, 1, NULL, 'other root', NULL, 0)")
    con.execute("INSERT INTO post VALUES(3, 1, 1, 'root parent', 'quote', 0)")
    con.commit()
    con.close()

    def _pair(pair_id, parent, agent=2):
        return CandidatePair(
            pair_id=pair_id, parent_item_id=parent, agent_id=agent, round_id=1,
            stratum_id=f"agent:{agent}:round:1", selection_probability=0.4,
            treatment_probability=0.5, parent_first_readable_round=1,
            prior_exposure_count=0, complete_same_action_opportunity=True)

    frame = SamplingFrame(
        frame_id="frame:evidence",
        parent_records=(
            ParentEligibility("post:1", author_agent_id=0, created_round=0),
            ParentEligibility("post:3", author_agent_id=1, created_round=0),
        ),
        excluded_recipient_agent_ids=(0, 1, 9),
        candidate_pairs=(_pair("pair:root", "post:1"),
                         _pair("pair:derived", "post:3")),
    )
    evidence = load_frame_eligibility_evidence(frame, db, ())
    by_pair = {row.pair_id: row for row in evidence.pair_evidence}
    assert by_pair["pair:root"].complete_same_action_opportunity is True
    assert by_pair["pair:derived"].complete_same_action_opportunity is False
    with pytest.raises(ValueError, match="complete same-action opportunity"):
        validate_frame_provenance(frame, evidence)


def test_marker_posts_fail_closed_on_wrong_database_round(tmp_path):
    """The banked round labels must be observed in the DB, not copied from the frozen constants."""
    db = str(tmp_path / "oasis.db")
    _build_synthetic_oasis_db(db)
    con = sqlite3.connect(db)
    try:
        for k, expected_round in enumerate(pspec.PILOT_INJECTION_ROUNDS):
            actual_round = expected_round + 1 if k == 0 else expected_round
            con.execute(
                "INSERT INTO post(post_id,user_id,original_post_id,content,quote_content,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (10 + k, hs.NEWS_USER_AGENT_ID, None, hs.NEWS_POOL[k], None, actual_round),
            )
        con.commit()
    finally:
        con.close()

    with pytest.raises(ValueError, match="frozen schedule"):
        marker_post_ids(db)
