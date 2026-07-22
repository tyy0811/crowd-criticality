from __future__ import annotations

from dataclasses import replace
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
