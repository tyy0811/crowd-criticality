"""Fixed-frame refresh intervention core for the causal reply probe.

Pure Task-3 core: no OASIS import. The controller consumes a frozen, pre-serialized
``SamplingFrame`` and realizes the exact categorical selection and treatment/holdout
before the prompt feed is returned; it can never create or admit a candidate at
refresh time. Served feed rule (Task-3 driver choice, symmetric across arms): both
arms strip the parent and the filler from the background, then serve the
experimental item — the parent (treated) or its registered filler (holdout) — in
the first slot, truncated back to the background length, so the arms differ only
in which item occupies the experimental slot.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Mapping

import numpy as np

from .causal_probe_records import (
    Assignment,
    CandidatePair,
    SamplingFrame,
    StratumDraw,
    sampling_frame_sha256,
)
from .causal_probe_validation import validate_sampling_frame

__all__ = (
    "PROBE_RNG_STREAM_SELECTION",
    "PROBE_RNG_STREAM_TREATMENT",
    "ServiceRecord",
    "CausalRefreshController",
    "apply_causal_refresh",
    "build_probe_rngs",
    "post_item_id",
    "wrap_background_refresh",
)

# Namespaced spawn keys for the two probe streams; disjoint from the harness_spec
# graph/news streams by construction (values far outside that registry).
PROBE_RNG_STREAM_SELECTION = 901
PROBE_RNG_STREAM_TREATMENT = 902


def build_probe_rngs(seed: int) -> tuple[np.random.Generator, np.random.Generator]:
    """Distinct spawn-key NumPy streams for the selection and treatment draws."""
    selection = np.random.default_rng(
        np.random.SeedSequence(seed, spawn_key=(PROBE_RNG_STREAM_SELECTION,))
    )
    treatment = np.random.default_rng(
        np.random.SeedSequence(seed, spawn_key=(PROBE_RNG_STREAM_TREATMENT,))
    )
    return selection, treatment


def post_item_id(post: object) -> str:
    """Item ID of a served OASIS post dict under the export convention ``post:<id>``."""
    if not isinstance(post, dict) or "post_id" not in post:
        raise TypeError("feed items must be OASIS post dicts carrying 'post_id'")
    return f"post:{post['post_id']}"


@dataclass(frozen=True)
class ServiceRecord:
    """Pre-outcome service verification logged at the refresh boundary.

    `parent_seen_in_background` carries the OUTCOME semantics: the parent is
    visible in the FINAL SERVED feed beyond the intentional experimental
    serving (treated: any duplication; holdout: any occurrence) — a protocol
    breach, impossible when the feed builder succeeds. A benign raw-background
    occurrence that the builder deduplicated is recorded separately as the
    diagnostic `parent_in_raw_background` and is NOT leakage."""

    assignment_id: str
    pair_id: str
    selection_probability: float
    treatment_probability: float
    parent_served: bool
    parent_seen_in_background: bool
    parent_in_raw_background: bool
    feed_length_before: int
    feed_length_after: int


class CausalRefreshController:
    """Realize stratum draws and treatment over a frozen sampling frame."""

    def __init__(
        self,
        frame: SamplingFrame,
        selection_rng: object,
        treatment_rng: object,
        *,
        parent_posts: Mapping[str, object],
        filler_posts: Mapping[str, object],
    ) -> None:
        validate_sampling_frame(frame)
        self._frame = frame
        self._frame_sha256 = sampling_frame_sha256(frame)
        self._selection_rng = selection_rng
        self._treatment_rng = treatment_rng

        parent_ids = {parent.parent_item_id for parent in frame.parent_records}
        if set(parent_posts) != parent_ids:
            raise ValueError(
                "parent_posts must cover exactly the frame's registered parents"
            )
        if set(filler_posts) != parent_ids:
            raise ValueError(
                "filler_posts must register exactly one filler per parent"
            )
        authors = {
            parent.parent_item_id: parent.author_agent_id
            for parent in frame.parent_records
        }
        for parent_id, post in parent_posts.items():
            if post_item_id(post) != parent_id:
                raise ValueError(
                    f"parent post registered under {parent_id!r} carries a "
                    f"different post identity"
                )
            if post.get("user_id") != authors[parent_id]:
                raise ValueError(
                    f"parent post {parent_id!r} author does not match the registry"
                )
        self._filler_item_ids: dict[str, str] = {}
        for parent_id, post in filler_posts.items():
            filler_item_id = post_item_id(post)
            if filler_item_id in parent_ids:
                raise ValueError(
                    f"filler for {parent_id!r} collides with a registered parent"
                )
            self._filler_item_ids[parent_id] = filler_item_id
        self._parent_posts = dict(parent_posts)
        self._filler_posts = dict(filler_posts)

        self._pairs_by_stratum: dict[str, tuple[CandidatePair, ...]] = {}
        self._stratum_by_agent_round: dict[tuple[int, int], str] = {}
        self._round_of_stratum: dict[str, int] = {}
        for pair in frame.candidate_pairs:
            self._pairs_by_stratum.setdefault(pair.stratum_id, ())
            self._pairs_by_stratum[pair.stratum_id] += (pair,)
            self._stratum_by_agent_round[(pair.agent_id, pair.round_id)] = (
                pair.stratum_id
            )
            self._round_of_stratum[pair.stratum_id] = pair.round_id

        self._draws: list[StratumDraw] = []
        self._assignments: list[Assignment] = []
        self._services: list[ServiceRecord] = []
        self._drawn_strata: set[str] = set()
        self._max_seen_round: int | None = None

    @property
    def frame(self) -> SamplingFrame:
        return self._frame

    @property
    def frame_sha256(self) -> str:
        return self._frame_sha256

    @property
    def draws(self) -> tuple[StratumDraw, ...]:
        return tuple(self._draws)

    @property
    def assignments(self) -> tuple[Assignment, ...]:
        return tuple(self._assignments)

    @property
    def services(self) -> tuple[ServiceRecord, ...]:
        return tuple(self._services)

    def has_stratum(self, agent_id: int, round_id: int) -> bool:
        return (agent_id, round_id) in self._stratum_by_agent_round

    def assert_no_pending_exposure(
        self, agent_id: int, round_id: int, posts: tuple
    ) -> None:
        """Fail closed if a served feed exposes a registered parent to its
        assigned recipient while that recipient's stratum is still undrawn.

        The frame's zero-prior-exposure premise is verified pre-draw by the
        eligibility evidence; this guard closes the runtime window between that
        verification and the stratum draw (e.g. an organic refresh in an
        unregistered round serving the future experimental parent)."""
        pending_parents = {
            pair.parent_item_id
            for pair in self._frame.candidate_pairs
            if pair.agent_id == agent_id
            and pair.stratum_id not in self._drawn_strata
        }
        if not pending_parents:
            return
        served = {post_item_id(post) for post in posts}
        leaked = pending_parents & served
        if leaked:
            raise ValueError(
                f"isolation breach: registered parent(s) {sorted(leaked)!r} "
                f"served to recipient {agent_id} in round {round_id} before "
                f"the stratum draw (fail-closed)")

    def _check_frame_unchanged(self) -> None:
        if sampling_frame_sha256(self._frame) != self._frame_sha256:
            raise ValueError(
                "sampling frame content changed after controller construction"
            )

    def _enter_stratum(self, agent_id: int, round_id: int) -> str:
        stratum_id = self._stratum_by_agent_round.get((agent_id, round_id))
        if stratum_id is None:
            raise ValueError(
                f"no registered stratum for agent-round ({agent_id}, {round_id})"
            )
        if stratum_id in self._drawn_strata:
            raise ValueError(f"stratum {stratum_id!r} already has a draw")
        if self._max_seen_round is not None and round_id < self._max_seen_round:
            raise ValueError(
                "refresh rounds must be non-decreasing across stratum draws"
            )
        if self._max_seen_round is None or round_id > self._max_seen_round:
            undrawn_earlier = [
                stratum
                for stratum, stratum_round in self._round_of_stratum.items()
                if stratum_round < round_id and stratum not in self._drawn_strata
            ]
            if undrawn_earlier:
                raise ValueError(
                    "cannot advance the round with undrawn earlier-round strata: "
                    + ", ".join(sorted(undrawn_earlier))
                )
            self._max_seen_round = round_id
        return stratum_id

    def _assert_no_selection_isolation(
        self, agent_id: int, round_id: int, background_posts: tuple
    ) -> None:
        """Fail closed if a no-selection draw's returned background exposes a
        registered parent to this recipient: a same-round candidate parent for
        this agent-round, or a parent registered to one of this agent's
        later-round strata that remains undrawn."""
        same_round_parents = {
            pair.parent_item_id for pair in self._frame.candidate_pairs
            if pair.agent_id == agent_id and pair.round_id == round_id
        }
        future_pending_parents = {
            pair.parent_item_id for pair in self._frame.candidate_pairs
            if pair.agent_id == agent_id and pair.round_id > round_id
            and pair.stratum_id not in self._drawn_strata
        }
        served = {post_item_id(post) for post in background_posts}
        same_leak = same_round_parents & served
        if same_leak:
            raise ValueError(
                f"isolation breach: same-round registered parent(s) "
                f"{sorted(same_leak)!r} served organically to recipient "
                f"{agent_id} on a no-selection draw (fail-closed)")
        future_leak = future_pending_parents & served
        if future_leak:
            raise ValueError(
                f"isolation breach: future-round registered parent(s) "
                f"{sorted(future_leak)!r} served to recipient {agent_id} on a "
                f"no-selection draw before their stratum draw (fail-closed)")

    def _draw_selection(self, stratum_id: str) -> CandidatePair | None:
        uniform = float(self._selection_rng.random())
        if not 0.0 <= uniform < 1.0 or not math.isfinite(uniform):
            raise ValueError("selection draw outside [0, 1)")
        cumulative = 0.0
        for pair in self._pairs_by_stratum[stratum_id]:
            cumulative += pair.selection_probability
            if uniform < cumulative:
                return pair
        return None

    def _build_feed(
        self, pair: CandidatePair, treated: bool, background_posts: tuple
    ) -> tuple[tuple, bool, bool]:
        """Serve the experimental slot with full isolation:

        - ALL of this agent's SAME-ROUND registered parents are stripped from
          the background (the selector alone decides serving — an unselected
          co-stratum parent must never ride in organically);
        - a parent registered to one of this agent's LATER-round undrawn strata
          appearing in the background is a pre-draw exposure breach → raise;
        - a stripped background that cannot preserve the feed length (feed
          shrinkage) fails closed → raise;
        - the returned breach flag carries the served-feed semantics (treated:
          duplication beyond the intentional serving; holdout: any parent
          occurrence) — impossible when this builder returns."""
        parent_item = pair.parent_item_id
        filler_item = self._filler_item_ids[parent_item]
        if not background_posts:
            raise ValueError("cannot serve an experimental item into an empty feed")
        background_ids = [post_item_id(post) for post in background_posts]

        agent_pairs = [
            candidate for candidate in self._frame.candidate_pairs
            if candidate.agent_id == pair.agent_id
        ]
        later_pending_parents = {
            candidate.parent_item_id for candidate in agent_pairs
            if candidate.round_id > pair.round_id
            and candidate.stratum_id not in self._drawn_strata
        }
        leaked_later = later_pending_parents & set(background_ids)
        if leaked_later:
            raise ValueError(
                f"isolation breach: future-round registered parent(s) "
                f"{sorted(leaked_later)!r} served to recipient {pair.agent_id} "
                f"before their stratum draw (fail-closed)")

        same_round_parents = {
            candidate.parent_item_id for candidate in agent_pairs
            if candidate.round_id == pair.round_id
        }
        strip = same_round_parents | {filler_item}
        parent_in_raw_background = parent_item in background_ids
        base = tuple(
            post
            for post, item_id in zip(background_posts, background_ids)
            if item_id not in strip
        )
        served = (
            self._parent_posts[parent_item]
            if treated
            else self._filler_posts[parent_item]
        )
        feed = ((served,) + base)[: len(background_posts)]
        if len(feed) != len(background_posts):
            raise ValueError(
                "feed shrinkage: the stripped background cannot preserve the "
                "feed length (fail-closed)")
        served_ids = [post_item_id(post) for post in feed]
        if treated:
            served_breach = served_ids.count(parent_item) != 1
        else:
            served_breach = parent_item in served_ids
        return feed, parent_in_raw_background, served_breach

    def refresh(
        self, agent_id: int, round_id: int, background_posts: tuple
    ) -> tuple:
        """Serve one stratum draw; log the complete ledger before returning."""
        self._check_frame_unchanged()
        if type(agent_id) is not int or type(round_id) is not int:
            raise TypeError("agent_id and round_id must be exactly int")
        if type(background_posts) is not tuple:
            raise TypeError("background_posts must be exactly tuple")

        stratum_id = self._enter_stratum(agent_id, round_id)
        pair = self._draw_selection(stratum_id)
        self._drawn_strata.add(stratum_id)

        if pair is None:
            # No experimental item is served, so the invariant "a registered
            # parent reaches a recipient's feed only through controlled serving"
            # must be checked directly on the returned background — the strip/
            # serve path in _build_feed does not run here. A same-round
            # candidate parent for this stratum, or a future-round undrawn
            # parent for this agent, appearing organically is an uncontrolled
            # exposure (fail-closed).
            self._assert_no_selection_isolation(agent_id, round_id, background_posts)
            self._draws.append(
                StratumDraw(
                    frame_id=self._frame.frame_id,
                    stratum_id=stratum_id,
                    selected_pair_id=None,
                )
            )
            return background_posts

        treatment_uniform = float(self._treatment_rng.random())
        if not 0.0 <= treatment_uniform < 1.0 or not math.isfinite(treatment_uniform):
            raise ValueError("treatment draw outside [0, 1) (fail-closed)")
        treated = bool(treatment_uniform < pair.treatment_probability)
        feed, parent_in_raw_background, served_breach = self._build_feed(
            pair, treated, background_posts)
        self._draws.append(
            StratumDraw(
                frame_id=self._frame.frame_id,
                stratum_id=stratum_id,
                selected_pair_id=pair.pair_id,
            )
        )
        assignment = Assignment(
            assignment_id=f"assignment:{pair.pair_id}",
            frame_id=self._frame.frame_id,
            pair_id=pair.pair_id,
            filler_item_id=self._filler_item_ids[pair.parent_item_id],
            treated=treated,
        )
        self._assignments.append(assignment)
        self._services.append(
            ServiceRecord(
                assignment_id=assignment.assignment_id,
                pair_id=pair.pair_id,
                selection_probability=pair.selection_probability,
                treatment_probability=pair.treatment_probability,
                parent_served=treated,
                parent_seen_in_background=served_breach,
                parent_in_raw_background=parent_in_raw_background,
                feed_length_before=len(background_posts),
                feed_length_after=len(feed),
            )
        )
        return feed


async def apply_causal_refresh(base_refresh, platform, controller, agent_id):
    """Realize the fixed-frame intervention at an OASIS Platform's refresh boundary.

    Delegates ordinary refresh construction to ``base_refresh`` (the platform's own
    refresh), applies the controller before the posts reach prompt conversion, and
    re-records the refresh trace so its served IDs always equal the returned feed.
    Duck-typed on the Platform surface (``sandbox_clock``, ``pl_utils``) so this
    module never imports OASIS; safe here because ``Platform.running`` awaits each
    action inline (no concurrent refreshes on one platform instance).
    """
    round_id = int(platform.sandbox_clock.time_step)
    if controller is None:
        return await base_refresh(agent_id)
    if not controller.has_stratum(agent_id, round_id):
        result = await base_refresh(agent_id)
        if isinstance(result, dict) and result.get("success") is True and (
            "posts" in result
        ):
            controller.assert_no_pending_exposure(
                agent_id, round_id, tuple(result["posts"]))
        return result

    utils = platform.pl_utils
    had_instance_record = "_record_trace" in utils.__dict__
    original_record = utils._record_trace
    captured = []

    def _capture(user_id, action_type, action_info, current_time=None):
        captured.append((user_id, action_type, action_info))

    utils._record_trace = _capture
    try:
        result = await base_refresh(agent_id)
    finally:
        if had_instance_record:
            utils._record_trace = original_record
        else:
            del utils._record_trace

    if not (isinstance(result, dict) and result.get("success") is True and "posts" in result):
        raise RuntimeError(
            f"registered stratum (agent {agent_id}, round {round_id}) background "
            f"refresh failed: {result!r}"
        )
    feed = controller.refresh(agent_id, round_id, tuple(result["posts"]))
    refresh_traces = [row for row in captured if row[1] == "refresh"]
    if len(refresh_traces) != 1:
        raise RuntimeError(
            "expected exactly one background refresh trace record (fail-closed)"
        )
    user_id, action_type, action_info = refresh_traces[0]
    final_info = dict(action_info)
    final_info["posts"] = list(feed)
    original_record(user_id, action_type, final_info)
    return {"success": True, "posts": list(feed)}


def wrap_background_refresh(
    background_refresh: Callable[..., tuple],
    controller: CausalRefreshController | None = None,
) -> Callable[..., tuple]:
    """Default path: with no controller, the background refresh object is returned
    unchanged and no causal record can be emitted."""
    if controller is None:
        return background_refresh

    def _refresh(agent_id: int, round_id: int, *args: object, **kwargs: object) -> tuple:
        background = background_refresh(agent_id, round_id, *args, **kwargs)
        return controller.refresh(agent_id, round_id, tuple(background))

    return _refresh
