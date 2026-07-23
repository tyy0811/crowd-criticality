from __future__ import annotations

from dataclasses import replace
import os
import sqlite3

import pytest

from critaudit.sim.harness.causal_probe_records import (
    CandidatePair,
    ParentEligibility,
    SamplingFrame,
    sampling_frame_sha256,
    sampling_frame_to_bytes,
)
from critaudit.sim.harness.causal_refresh import (
    CausalRefreshController,
    build_probe_rngs,
    wrap_background_refresh,
)


# --- OASIS-compatible fixture DB (schemas verbatim from the installed camel-oasis 0.2.5
#     social_platform/schema/*.sql; FK targets omitted tables are unenforced in SQLite) ---------

_POST_COLUMNS = (
    "post_id",
    "user_id",
    "original_post_id",
    "content",
    "quote_content",
    "created_at",
    "num_likes",
    "num_dislikes",
    "num_shares",
)


def _build_fixture_db(path: str) -> None:
    """Two registered parents (posts 1, 2), distinct fillers (posts 3, 4), two recipients
    (agents 20, 21) whose rec rows carry only organic background posts (5, 6)."""
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE post (
            post_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            original_post_id INTEGER,
            content TEXT DEFAULT '',
            quote_content TEXT,
            created_at DATETIME,
            num_likes INTEGER DEFAULT 0,
            num_dislikes INTEGER DEFAULT 0,
            num_shares INTEGER DEFAULT 0,
            num_reports INTEGER DEFAULT 0
        );
        CREATE TABLE rec (
            user_id INTEGER,
            post_id INTEGER,
            PRIMARY KEY(user_id, post_id)
        );
        CREATE TABLE follow (
            follow_id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id INTEGER,
            followee_id INTEGER,
            created_at DATETIME
        );
        CREATE TABLE trace (
            user_id INTEGER,
            created_at DATETIME,
            action TEXT,
            info TEXT,
            PRIMARY KEY(user_id, created_at, action, info)
        );
        """
    )
    posts = (
        (1, 10, None, "parent post a", None, 1.0),
        (2, 11, None, "parent post b", None, 2.0),
        (3, 12, None, "filler post a", None, 1.0),
        (4, 12, None, "filler post b", None, 2.0),
        (5, 13, None, "background post one", None, 1.0),
        (6, 13, None, "background post two", None, 2.0),
    )
    for post_id, user_id, orig, content, quote, created in posts:
        con.execute(
            "INSERT INTO post(post_id, user_id, original_post_id, content, quote_content,"
            " created_at) VALUES(?,?,?,?,?,?)",
            (post_id, user_id, orig, content, quote, created),
        )
        con.execute(
            "INSERT INTO trace VALUES(?,?,?,?)",
            (user_id, created, "create_post", '{"post_id": %d}' % post_id),
        )
    for follower, followee in ((20, 10), (20, 13), (21, 11), (21, 13)):
        con.execute(
            "INSERT INTO follow(follower_id, followee_id, created_at) VALUES(?,?,0)",
            (follower, followee),
        )
    for user_id, post_id in ((20, 5), (20, 6), (21, 5), (21, 6)):
        con.execute("INSERT INTO rec VALUES(?,?)", (user_id, post_id))
    con.commit()
    con.close()


def _post_dict(db_path: str, post_id: int) -> dict:
    con = sqlite3.connect(db_path)
    row = con.execute(
        "SELECT post_id, user_id, original_post_id, content, quote_content, created_at,"
        " num_likes, num_dislikes, num_shares FROM post WHERE post_id = ?",
        (post_id,),
    ).fetchone()
    con.close()
    assert row is not None
    return dict(zip(_POST_COLUMNS, row))


def _background_refresh(db_path: str):
    """Fake background refresh: the platform.refresh rec-table read without OASIS."""

    def refresh(agent_id: int, round_id: int) -> tuple:
        con = sqlite3.connect(db_path)
        rows = con.execute(
            "SELECT post.post_id, post.user_id, post.original_post_id, post.content,"
            " post.quote_content, post.created_at, post.num_likes, post.num_dislikes,"
            " post.num_shares FROM rec JOIN post ON rec.post_id = post.post_id"
            " WHERE rec.user_id = ? ORDER BY post.post_id",
            (agent_id,),
        ).fetchall()
        con.close()
        return tuple(dict(zip(_POST_COLUMNS, row)) for row in rows)

    return refresh


def _frame() -> SamplingFrame:
    return SamplingFrame(
        frame_id="frame:refresh",
        parent_records=(
            ParentEligibility("post:1", author_agent_id=10, created_round=1),
            ParentEligibility("post:2", author_agent_id=11, created_round=2),
        ),
        excluded_recipient_agent_ids=(10, 11, 99),
        candidate_pairs=(
            CandidatePair(
                pair_id="pair:1",
                parent_item_id="post:1",
                agent_id=20,
                round_id=3,
                stratum_id="agent:20:round:3",
                selection_probability=0.4,
                treatment_probability=0.5,
                parent_first_readable_round=3,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
            CandidatePair(
                pair_id="pair:2",
                parent_item_id="post:2",
                agent_id=20,
                round_id=3,
                stratum_id="agent:20:round:3",
                selection_probability=0.4,
                treatment_probability=0.5,
                parent_first_readable_round=3,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
            CandidatePair(
                pair_id="pair:3",
                parent_item_id="post:2",
                agent_id=21,
                round_id=4,
                stratum_id="agent:21:round:4",
                selection_probability=0.5,
                treatment_probability=0.5,
                parent_first_readable_round=4,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
        ),
    )


class _Stream:
    """Deterministic scripted stand-in for a NumPy Generator's random()."""

    def __init__(self, *values: float) -> None:
        self._values = list(values)

    def random(self) -> float:
        return self._values.pop(0)


def _controller(db_path: str, selection: _Stream, treatment: _Stream) -> CausalRefreshController:
    return CausalRefreshController(
        _frame(),
        selection,
        treatment,
        parent_posts={"post:1": _post_dict(db_path, 1), "post:2": _post_dict(db_path, 2)},
        filler_posts={"post:1": _post_dict(db_path, 3), "post:2": _post_dict(db_path, 4)},
    )


@pytest.fixture()
def db_path(tmp_path) -> str:
    path = str(tmp_path / "oasis.db")
    _build_fixture_db(path)
    return path


# --- fixed frame first, then the controller ---------------------------------------------------


def test_frame_serializes_before_controller_and_hash_is_stable(db_path):
    frame = _frame()
    frozen_bytes = sampling_frame_to_bytes(frame)
    frozen_sha = sampling_frame_sha256(frame)

    controller = CausalRefreshController(
        frame,
        _Stream(0.10),
        _Stream(0.10),
        parent_posts={"post:1": _post_dict(db_path, 1), "post:2": _post_dict(db_path, 2)},
        filler_posts={"post:1": _post_dict(db_path, 3), "post:2": _post_dict(db_path, 4)},
    )
    controller.refresh(20, 3, _background_refresh(db_path)(20, 3))

    assert sampling_frame_to_bytes(frame) == frozen_bytes
    assert sampling_frame_sha256(frame) == frozen_sha


# --- treatment arm ----------------------------------------------------------------------------


def test_treatment_serves_parent_exactly_once_and_preserves_length(db_path):
    controller = _controller(db_path, _Stream(0.10), _Stream(0.10))
    background = _background_refresh(db_path)(20, 3)
    background_with_leak = (_post_dict(db_path, 1),) + background

    feed = controller.refresh(20, 3, background_with_leak)

    parent_ids = [post["post_id"] for post in feed]
    assert len(feed) == len(background_with_leak)
    assert parent_ids.count(1) == 1
    assert feed[0]["post_id"] == 1

    (draw,) = controller.draws
    assert draw.frame_id == "frame:refresh"
    assert draw.stratum_id == "agent:20:round:3"
    assert draw.selected_pair_id == "pair:1"

    (assignment,) = controller.assignments
    assert assignment.frame_id == "frame:refresh"
    assert assignment.pair_id == "pair:1"
    assert assignment.filler_item_id == "post:3"
    assert assignment.treated is True

    (service,) = controller.services
    assert service.assignment_id == assignment.assignment_id
    assert service.pair_id == "pair:1"
    assert service.selection_probability == 0.4
    assert service.treatment_probability == 0.5
    assert service.parent_served is True
    assert service.parent_seen_in_background is True
    assert service.feed_length_before == len(background_with_leak)
    assert service.feed_length_after == len(feed)


def test_treatment_without_background_leak_records_clean_service(db_path):
    controller = _controller(db_path, _Stream(0.10), _Stream(0.10))
    background = _background_refresh(db_path)(20, 3)

    feed = controller.refresh(20, 3, background)

    assert len(feed) == len(background)
    assert [post["post_id"] for post in feed].count(1) == 1
    (service,) = controller.services
    assert service.parent_served is True
    assert service.parent_seen_in_background is False
    assert service.feed_length_before == service.feed_length_after == len(background)


# --- holdout arm ------------------------------------------------------------------------------


def test_holdout_serves_filler_and_never_the_parent(db_path):
    controller = _controller(db_path, _Stream(0.10), _Stream(0.90))
    background = _background_refresh(db_path)(20, 3)
    background_with_leak = (_post_dict(db_path, 1),) + background

    feed = controller.refresh(20, 3, background_with_leak)

    served_ids = [post["post_id"] for post in feed]
    assert len(feed) == len(background_with_leak)
    assert 1 not in served_ids
    assert served_ids.count(3) == 1
    assert feed[0]["post_id"] == 3

    (assignment,) = controller.assignments
    assert assignment.treated is False
    assert assignment.filler_item_id == "post:3"
    (service,) = controller.services
    assert service.parent_served is False
    assert service.parent_seen_in_background is True
    assert service.feed_length_before == service.feed_length_after == len(feed)


# --- categorical no-selection -----------------------------------------------------------------


def test_no_selection_records_explicit_draw_and_leaves_feed_unchanged(db_path):
    controller = _controller(db_path, _Stream(0.85), _Stream())
    background = _background_refresh(db_path)(20, 3)

    feed = controller.refresh(20, 3, background)

    assert feed is background
    (draw,) = controller.draws
    assert draw.selected_pair_id is None
    assert controller.assignments == ()
    assert controller.services == ()


def test_second_pair_selects_by_cumulative_mass(db_path):
    controller = _controller(db_path, _Stream(0.50), _Stream(0.10))
    feed = controller.refresh(20, 3, _background_refresh(db_path)(20, 3))
    (draw,) = controller.draws
    assert draw.selected_pair_id == "pair:2"
    assert [post["post_id"] for post in feed].count(2) == 1


# --- stratum ledger fail-closed behavior ------------------------------------------------------


def test_unknown_agent_round_fails_closed(db_path):
    controller = _controller(db_path, _Stream(0.10), _Stream(0.10))
    with pytest.raises(ValueError, match="stratum"):
        controller.refresh(30, 3, _background_refresh(db_path)(20, 3))


def test_duplicate_stratum_fails_closed(db_path):
    controller = _controller(db_path, _Stream(0.85, 0.85), _Stream())
    background = _background_refresh(db_path)(20, 3)
    controller.refresh(20, 3, background)
    with pytest.raises(ValueError, match="draw"):
        controller.refresh(20, 3, background)


def test_missing_earlier_round_fails_closed_at_round_advance(db_path):
    controller = _controller(db_path, _Stream(0.10), _Stream(0.10))
    with pytest.raises(ValueError, match="round"):
        controller.refresh(21, 4, _background_refresh(db_path)(21, 4))


def test_every_registered_stratum_yields_exactly_one_draw(db_path):
    controller = _controller(db_path, _Stream(0.85, 0.85), _Stream())
    controller.refresh(20, 3, _background_refresh(db_path)(20, 3))
    controller.refresh(21, 4, _background_refresh(db_path)(21, 4))
    assert len(controller.draws) == 2
    assert {draw.stratum_id for draw in controller.draws} == {
        "agent:20:round:3",
        "agent:21:round:4",
    }
    with pytest.raises(ValueError):
        controller.refresh(20, 3, _background_refresh(db_path)(20, 3))


# --- frame integrity fail-closed --------------------------------------------------------------


def test_prior_exposure_fails_closed_at_construction(db_path):
    frame = _frame()
    tainted = replace(
        frame,
        candidate_pairs=(
            replace(frame.candidate_pairs[0], prior_exposure_count=1),
        )
        + frame.candidate_pairs[1:],
    )
    with pytest.raises(ValueError, match="prior exposure"):
        CausalRefreshController(
            tainted,
            _Stream(0.10),
            _Stream(0.10),
            parent_posts={"post:1": _post_dict(db_path, 1), "post:2": _post_dict(db_path, 2)},
            filler_posts={"post:1": _post_dict(db_path, 3), "post:2": _post_dict(db_path, 4)},
        )


def test_two_strata_for_one_agent_round_fail_closed(db_path):
    frame = _frame()
    tainted = replace(
        frame,
        candidate_pairs=frame.candidate_pairs[:1]
        + (replace(frame.candidate_pairs[1], stratum_id="agent:20:round:3b"),)
        + frame.candidate_pairs[2:],
    )
    with pytest.raises(ValueError, match="stratum"):
        CausalRefreshController(
            tainted,
            _Stream(0.10),
            _Stream(0.10),
            parent_posts={"post:1": _post_dict(db_path, 1), "post:2": _post_dict(db_path, 2)},
            filler_posts={"post:1": _post_dict(db_path, 3), "post:2": _post_dict(db_path, 4)},
        )


def test_mutable_frame_content_fails_closed(db_path):
    frame = _frame()
    controller = CausalRefreshController(
        frame,
        _Stream(0.10),
        _Stream(0.10),
        parent_posts={"post:1": _post_dict(db_path, 1), "post:2": _post_dict(db_path, 2)},
        filler_posts={"post:1": _post_dict(db_path, 3), "post:2": _post_dict(db_path, 4)},
    )
    object.__setattr__(frame, "frame_id", "frame:tampered")
    with pytest.raises(ValueError, match="frame"):
        controller.refresh(20, 3, _background_refresh(db_path)(20, 3))


def test_nontuple_candidate_pairs_fail_closed(db_path):
    frame = _frame()
    with pytest.raises(TypeError):
        CausalRefreshController(
            replace(frame, candidate_pairs=list(frame.candidate_pairs)),
            _Stream(0.10),
            _Stream(0.10),
            parent_posts={"post:1": _post_dict(db_path, 1), "post:2": _post_dict(db_path, 2)},
            filler_posts={"post:1": _post_dict(db_path, 3), "post:2": _post_dict(db_path, 4)},
        )


# --- post registry fail-closed ----------------------------------------------------------------


def test_parent_post_registry_must_cover_exactly_the_frame(db_path):
    with pytest.raises(ValueError, match="parent"):
        CausalRefreshController(
            _frame(),
            _Stream(0.10),
            _Stream(0.10),
            parent_posts={"post:1": _post_dict(db_path, 1)},
            filler_posts={"post:1": _post_dict(db_path, 3), "post:2": _post_dict(db_path, 4)},
        )


def test_parent_post_identity_mismatch_fails_closed(db_path):
    with pytest.raises(ValueError, match="post"):
        CausalRefreshController(
            _frame(),
            _Stream(0.10),
            _Stream(0.10),
            parent_posts={"post:1": _post_dict(db_path, 5), "post:2": _post_dict(db_path, 2)},
            filler_posts={"post:1": _post_dict(db_path, 3), "post:2": _post_dict(db_path, 4)},
        )


def test_filler_colliding_with_a_registered_parent_fails_closed(db_path):
    with pytest.raises(ValueError, match="filler"):
        CausalRefreshController(
            _frame(),
            _Stream(0.10),
            _Stream(0.10),
            parent_posts={"post:1": _post_dict(db_path, 1), "post:2": _post_dict(db_path, 2)},
            filler_posts={"post:1": _post_dict(db_path, 2), "post:2": _post_dict(db_path, 4)},
        )


def test_non_post_feed_items_fail_closed(db_path):
    controller = _controller(db_path, _Stream(0.10), _Stream(0.10))
    with pytest.raises(TypeError):
        controller.refresh(20, 3, ("not a post",))


def test_empty_background_feed_fails_closed_on_selection(db_path):
    controller = _controller(db_path, _Stream(0.10), _Stream(0.10))
    with pytest.raises(ValueError, match="feed"):
        controller.refresh(20, 3, ())


# --- refresh isolation: pending-exposure guard -------------------------------------------------


def test_pending_exposure_guard_fails_closed_before_the_stratum_draw(db_path):
    """An organic (unregistered-round) serving of a registered parent to its
    assigned recipient BEFORE that recipient's stratum draw is an isolation
    breach and must raise, never pass silently."""
    controller = _controller(db_path, _Stream(0.10), _Stream(0.10))
    parent_post = _post_dict(db_path, 1)
    with pytest.raises(ValueError, match="isolation"):
        controller.assert_no_pending_exposure(20, 2, (parent_post,))


def test_pending_exposure_guard_ignores_unrelated_agents_and_drawn_strata(db_path):
    controller = _controller(db_path, _Stream(0.10, 0.10), _Stream(0.10, 0.10))
    parent_post = _post_dict(db_path, 1)
    # an agent with no registered pair for this parent is unaffected
    controller.assert_no_pending_exposure(30, 2, (parent_post,))
    # recipient 21's only pair is parent post:2 — post:1 exposure is fine
    controller.assert_no_pending_exposure(21, 2, (parent_post,))
    # once agent 20's stratum is drawn, later organic exposure no longer raises
    controller.refresh(20, 3, _background_refresh(db_path)(20, 3))
    controller.assert_no_pending_exposure(20, 3, (parent_post,))


def test_apply_causal_refresh_guards_unregistered_rounds(db_path):
    """The platform-facing wrapper must route unregistered refreshes of a
    registered recipient through the pending-exposure guard (fail-open fix)."""
    import asyncio
    from types import SimpleNamespace

    from critaudit.sim.harness.causal_refresh import apply_causal_refresh

    controller = _controller(db_path, _Stream(0.10), _Stream(0.10))
    parent_post = _post_dict(db_path, 1)
    platform = SimpleNamespace(
        sandbox_clock=SimpleNamespace(time_step=2),
        pl_utils=SimpleNamespace(),
    )

    async def leaking_base_refresh(agent_id):
        return {"success": True, "posts": [parent_post]}

    with pytest.raises(ValueError, match="isolation"):
        asyncio.run(apply_causal_refresh(
            leaking_base_refresh, platform, controller, 20))

    async def clean_base_refresh(agent_id):
        return {"success": True, "posts": [_post_dict(db_path, 5)]}

    result = asyncio.run(apply_causal_refresh(
        clean_base_refresh, platform, controller, 20))
    assert result["posts"][0]["post_id"] == 5
    assert controller.draws == ()


# --- deterministic seeded streams -------------------------------------------------------------


def test_build_probe_rngs_streams_are_deterministic_and_distinct():
    selection_a, treatment_a = build_probe_rngs(7)
    selection_b, treatment_b = build_probe_rngs(7)
    selection_seq = [selection_a.random() for _ in range(4)]
    treatment_seq = [treatment_a.random() for _ in range(4)]
    assert selection_seq == [selection_b.random() for _ in range(4)]
    assert treatment_seq == [treatment_b.random() for _ in range(4)]
    assert selection_seq != treatment_seq


def test_seeded_controller_run_is_reproducible(db_path):
    def run() -> tuple:
        selection, treatment = build_probe_rngs(11)
        controller = _controller(db_path, selection, treatment)
        controller.refresh(20, 3, _background_refresh(db_path)(20, 3))
        controller.refresh(21, 4, _background_refresh(db_path)(21, 4))
        return controller.draws, controller.assignments

    assert run() == run()


# --- default-path equivalence -----------------------------------------------------------------


def test_wrapper_without_controller_is_the_background_refresh_object(db_path):
    background = _background_refresh(db_path)
    wrapped = wrap_background_refresh(background)
    assert wrapped is background
    assert wrapped(20, 3) == background(20, 3)


def test_wrapper_with_controller_delegates_to_refresh(db_path):
    controller = _controller(db_path, _Stream(0.85, 0.85), _Stream())
    wrapped = wrap_background_refresh(_background_refresh(db_path), controller)
    feed = wrapped(20, 3)
    assert feed == _background_refresh(db_path)(20, 3)
    assert len(controller.draws) == 1


# --- Task 4: installed-OASIS Platform integration (skipped where oasis is absent) --------------


def _integration_frame() -> SamplingFrame:
    """Fixed pre-run frame for the full-platform session: parents = posts 1 (agent 0) and
    2 (agent 1) created in round 0, first readable in round 1; recipients 2 and 3."""
    return SamplingFrame(
        frame_id="frame:integration",
        parent_records=(
            ParentEligibility("post:1", author_agent_id=0, created_round=0),
            ParentEligibility("post:2", author_agent_id=1, created_round=0),
        ),
        excluded_recipient_agent_ids=(0, 1, 5),
        candidate_pairs=(
            CandidatePair(
                pair_id="pair:1",
                parent_item_id="post:1",
                agent_id=2,
                round_id=1,
                stratum_id="agent:2:round:1",
                selection_probability=0.4,
                treatment_probability=0.5,
                parent_first_readable_round=1,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
            CandidatePair(
                pair_id="pair:2",
                parent_item_id="post:2",
                agent_id=2,
                round_id=1,
                stratum_id="agent:2:round:1",
                selection_probability=0.4,
                treatment_probability=0.5,
                parent_first_readable_round=1,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
            CandidatePair(
                pair_id="pair:3",
                parent_item_id="post:2",
                agent_id=3,
                round_id=1,
                stratum_id="agent:3:round:1",
                selection_probability=0.5,
                treatment_probability=0.5,
                parent_first_readable_round=1,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
        ),
    )


async def _drive_causal_session(tmp_path):
    from oasis import ActionType, AgentGraph, SocialAgent, make
    from oasis.social_platform.channel import Channel
    from oasis.social_platform.platform import Platform
    from oasis.social_platform.typing import RecsysType

    from critaudit.sim.harness import harness_spec as hs
    from critaudit.sim.harness.causal_probe import estimate_r_reply
    from critaudit.sim.harness.causal_probe_validation import (
        validate_frame_provenance,
        validate_outcomes,
    )
    from critaudit.sim.harness.causal_refresh import apply_causal_refresh
    from critaudit.sim.harness.oasis_adapter import (
        _make_news_sentinel_model,
        _new_user_info,
        _served_post_ids,
        collect_causal_outcomes,
        load_frame_eligibility_evidence,
        persist_evidence_artifacts,
        persist_frame_artifacts,
        read_trace_rows,
    )

    db_path = str(tmp_path / "causal_oasis.db")
    artifact_dir = str(tmp_path / "artifacts")

    frame = _integration_frame()
    pre_bytes = sampling_frame_to_bytes(frame)
    pre_sha = sampling_frame_sha256(frame)

    sentinel = _make_news_sentinel_model(
        model_id="fixture-model",
        endpoint_url="http://sentinel.invalid/v1",
        token="fixture-token",
        max_tokens=64,
        temperature=0.0,
        timeout=5,
        context_budget=1024,
    )

    class _CausalTestPlatform(Platform):
        """Delegates ordinary refresh construction to Platform, then applies the
        controller before the returned posts reach prompt conversion. The rec table
        is fixtured deterministically (organic posts 5 and 6 only)."""

        causal_controller = None

        async def refresh(self, agent_id):
            return await apply_causal_refresh(
                super().refresh, self, self.causal_controller, agent_id
            )

        async def update_rec_table(self):
            self.db_cursor.execute("DELETE FROM rec")
            for user_id, post_id in ((2, 5), (2, 6), (3, 5), (3, 6)):
                self.db_cursor.execute(
                    "INSERT INTO rec VALUES (?, ?)", (user_id, post_id)
                )
            self.db.commit()

    platform = _CausalTestPlatform(
        db_path=db_path,
        channel=Channel(),
        recsys_type=RecsysType(hs.RECSYS_TYPE),
        refresh_rec_post_count=3,
        max_rec_post_len=5,
        following_post_count=hs.FOLLOWING_POST_COUNT,
    )

    graph = AgentGraph()
    available = [
        ActionType(name)
        for name in ("create_post", "create_comment", "repost", "quote_post", "do_nothing")
    ]
    names = {
        0: "author_a",
        1: "author_b",
        2: "recipient_two",
        3: "recipient_three",
        4: "organic_author",
        5: "news_source",
    }
    for agent_id, name in names.items():
        graph.add_agent(
            SocialAgent(
                agent_id=agent_id,
                user_info=_new_user_info(
                    name=name, bio="fixture user", user_profile="fixture user"
                ),
                model=sentinel,
                available_actions=available,
            )
        )

    env = make(agent_graph=graph, platform=platform, database_path=db_path)
    await env.reset()
    try:
        created_ids = []
        for agent_id, content in (
            (0, "parent post a"),
            (1, "parent post b"),
            (4, "filler a"),
            (4, "filler b"),
            (4, "background one"),
            (4, "background two"),
        ):
            result = await graph.get_agent(agent_id).env.action.create_post(content)
            assert result.get("success") is True, result
            created_ids.append(result["post_id"])
        assert created_ids == [1, 2, 3, 4, 5, 6]

        await env.step({})  # advance to round 1; fixture rec rows land

        # -- pre-draw eligibility evidence from the actual DB and trace rows -----------
        trace_rows = read_trace_rows(db_path)
        evidence = load_frame_eligibility_evidence(frame, db_path, trace_rows)
        validate_frame_provenance(frame, evidence)
        assert evidence.news_user_agent_id == 5
        assert all(row.prior_exposure_count == 0 for row in evidence.pair_evidence)
        assert all(row.first_readable_round == 1 for row in evidence.pair_evidence)
        assert all(
            row.complete_same_action_opportunity is True
            for row in evidence.pair_evidence
        )

        wrong_author = replace(
            frame,
            parent_records=(
                replace(frame.parent_records[0], author_agent_id=4),
            )
            + frame.parent_records[1:],
        )
        with pytest.raises(ValueError, match="author"):
            validate_frame_provenance(
                wrong_author,
                load_frame_eligibility_evidence(wrong_author, db_path, trace_rows),
            )

        no_news_exclusion = replace(frame, excluded_recipient_agent_ids=(0, 1))
        with pytest.raises(ValueError, match="news user"):
            validate_frame_provenance(
                no_news_exclusion,
                load_frame_eligibility_evidence(
                    no_news_exclusion, db_path, trace_rows
                ),
            )

        persist_frame_artifacts(artifact_dir, frame)
        persist_evidence_artifacts(artifact_dir, evidence)

        # -- controller fixed after evidence, before the first draw --------------------
        parent_posts = {"post:1": _post_dict(db_path, 1), "post:2": _post_dict(db_path, 2)}
        filler_posts = {"post:1": _post_dict(db_path, 3), "post:2": _post_dict(db_path, 4)}
        controller = CausalRefreshController(
            frame,
            _Stream(0.10, 0.10),
            _Stream(0.10, 0.90),
            parent_posts=parent_posts,
            filler_posts=filler_posts,
        )
        platform.causal_controller = controller

        treated_result = await graph.get_agent(2).env.action.refresh()
        assert treated_result.get("success") is True, treated_result
        treated_ids = [post["post_id"] for post in treated_result["posts"]]
        assert treated_ids[0] == 1
        assert treated_ids.count(1) == 1
        assert len(treated_ids) == 2

        holdout_result = await graph.get_agent(3).env.action.refresh()
        assert holdout_result.get("success") is True, holdout_result
        holdout_ids = [post["post_id"] for post in holdout_result["posts"]]
        assert 2 not in holdout_ids
        assert holdout_ids[0] == 4
        assert len(holdout_ids) == 2

        respond = await graph.get_agent(2).env.action.create_comment(
            1, "reply to parent a"
        )
        assert respond.get("success") is True, respond

        await env.step({})  # advance to round 2, locking the outcome round
    finally:
        await env.close()

    # -- trace serves exactly the returned feeds, draws precede the outcome action -----
    con = sqlite3.connect(db_path)
    refresh_rows = con.execute(
        "SELECT rowid, user_id, info FROM trace WHERE action = 'refresh' ORDER BY rowid"
    ).fetchall()
    comment_rows = con.execute(
        "SELECT rowid, user_id FROM trace WHERE action = 'create_comment'"
    ).fetchall()
    con.close()
    assert len(refresh_rows) == 2
    refresh_by_user = {row[1]: row for row in refresh_rows}
    assert _served_post_ids(refresh_by_user[2][2]) == treated_ids
    assert _served_post_ids(refresh_by_user[3][2]) == holdout_ids
    (comment_row,) = comment_rows
    assert comment_row[1] == 2
    assert refresh_by_user[2][0] < comment_row[0]

    # -- complete persisted ledgers and the outcome join --------------------------------
    assert {draw.stratum_id for draw in controller.draws} == {
        "agent:2:round:1",
        "agent:3:round:1",
    }
    assert [draw.selected_pair_id for draw in controller.draws] == ["pair:1", "pair:3"]
    assert [assignment.treated for assignment in controller.assignments] == [True, False]

    outcomes = collect_causal_outcomes(controller, db_path)
    validate_outcomes(frame, controller.draws, controller.assignments, outcomes)
    outcomes_by_assignment = {outcome.assignment_id: outcome for outcome in outcomes}
    treated_outcome = outcomes_by_assignment["assignment:pair:1"]
    assert treated_outcome.direct_child_item_id == "comment:1"
    assert treated_outcome.direct_child_parent_id == "post:1"
    assert treated_outcome.child_author_agent_id == 2
    assert treated_outcome.child_round == 1
    holdout_outcome = outcomes_by_assignment["assignment:pair:3"]
    assert holdout_outcome.direct_child_item_id is None
    assert holdout_outcome.parent_served is False

    estimate = estimate_r_reply(frame, controller.draws, controller.assignments, outcomes)
    assert estimate.status == "design_only"
    assert estimate.response_count == 1

    # -- persisted frame bytes/hash equal the pre-run frame ------------------------------
    with open(os.path.join(artifact_dir, "causal_frame.json"), "rb") as artifact:
        assert artifact.read() == pre_bytes
    with open(os.path.join(artifact_dir, "causal_frame.sha256")) as artifact:
        assert artifact.read().strip() == pre_sha

    # -- exposure counting sees the causal serving itself --------------------------------
    post_rows = read_trace_rows(db_path)
    later_frame = replace(
        frame,
        candidate_pairs=frame.candidate_pairs
        + (
            CandidatePair(
                pair_id="pair:x",
                parent_item_id="post:1",
                agent_id=2,
                round_id=2,
                stratum_id="agent:2:round:2",
                selection_probability=0.5,
                treatment_probability=0.5,
                parent_first_readable_round=2,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
        ),
    )
    later_evidence = load_frame_eligibility_evidence(later_frame, db_path, post_rows)
    evidence_by_pair = {row.pair_id: row for row in later_evidence.pair_evidence}
    assert evidence_by_pair["pair:x"].prior_exposure_count == 1


def test_full_platform_causal_session(tmp_path):
    pytest.importorskip("oasis")
    import asyncio

    asyncio.run(_drive_causal_session(tmp_path))
