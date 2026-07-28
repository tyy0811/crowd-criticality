"""Fixed-frame one-generation scripted positive control for the causal reply probe.

Pure half: `build_scripted_control_frame` lays out a deterministic control frame with a
planted one-generation reproduction `plant_r`, drawing a FIXED binary potential response
for every candidate pair before any selection. `R_plant = mean_parent(sum q_ip)` is the
registered expectation; the hidden `R_gen_frame = mean_parent(sum y_ip)` is the frame's
realized generator truth. The estimator may read neither `q` nor any unobserved `y`;
only the scripted action policy consumes the truth. No OASIS, LLM, embedding,
similarity, or Hawkes import appears in this module's import surface — the platform
bridge imports lazily inside the function.

Bridge half: `run_scripted_oasis_control` drives the installed OASIS Platform with the
production `CausalRefreshController`, the real round clock and trace tables, and a
scripted non-LLM native-link policy, returning the complete frozen ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from critaudit.sim.harness.causal_probe_records import (
    Assignment,
    CandidatePair,
    ParentEligibility,
    ProbeManifest,
    SamplingFrame,
    StratumDraw,
    Outcome,
    frame_eligibility_evidence_sha256,
    frame_eligibility_evidence_to_bytes,
)
from critaudit.sim.harness.causal_probe_validation import (
    validate_frame_provenance,
    validate_sampling_frame,
)
from critaudit.sim.harness.causal_refresh import (
    PROBE_RNG_STREAM_SELECTION,
    PROBE_RNG_STREAM_TREATMENT,
    CausalRefreshController,
)

__all__ = (
    "CONTROL_SEED_STREAM",
    "CONTROL_RNG_STREAM_LAYOUT",
    "CONTROL_RNG_STREAM_RESPONSES",
    "PotentialResponse",
    "ControlTruth",
    "ScriptedReply",
    "ScriptedControlRun",
    "build_scripted_control_frame",
    "control_probe_rngs",
    "run_scripted_oasis_control",
    "scripted_action_for_assignment",
)

# Frozen namespace registry: seed-stream label -> spawn-key root. Manifests carry the
# label + raw seed; an unregistered label is rejected, so results cannot be relabeled
# onto another stream after the fact.
CONTROL_SEED_STREAM = "control:scripted"
_SEED_STREAM_KEYS = {CONTROL_SEED_STREAM: 911}

# Distinct SeedSequence namespaces inside a control build. The layout stream is
# registered for future stochastic layouts; the current layout is closed-form and
# draws nothing, so determinism does not lean on it.
CONTROL_RNG_STREAM_LAYOUT = 916
CONTROL_RNG_STREAM_RESPONSES = 917


@dataclass(frozen=True)
class PotentialResponse:
    pair_id: str
    response_probability: float
    potential_response: bool


@dataclass(frozen=True)
class ControlTruth:
    frame_id: str
    r_plant: float
    r_gen_frame: float
    potential_responses: tuple[PotentialResponse, ...]


@dataclass(frozen=True)
class ScriptedReply:
    assignment_id: str
    pair_id: str


@dataclass(frozen=True)
class ScriptedControlRun:
    manifest: ProbeManifest
    frame_bytes: bytes
    frame_sha256: str
    eligibility_evidence_bytes: bytes
    eligibility_evidence_sha256: str
    draws: tuple[StratumDraw, ...]
    assignments: tuple[Assignment, ...]
    outcomes: tuple[Outcome, ...]


def control_probe_rngs(seed_stream_id: str, seed: int):
    """Selection/treatment generators on the frozen namespace for `seed_stream_id`."""
    key = _SEED_STREAM_KEYS.get(seed_stream_id)
    if key is None:
        raise ValueError(f"unregistered seed stream {seed_stream_id!r} (fail-closed)")
    selection = np.random.default_rng(
        np.random.SeedSequence(seed, spawn_key=(key, PROBE_RNG_STREAM_SELECTION))
    )
    treatment = np.random.default_rng(
        np.random.SeedSequence(seed, spawn_key=(key, PROBE_RNG_STREAM_TREATMENT))
    )
    return selection, treatment


def build_scripted_control_frame(
    parent_count: int,
    recipients_per_parent: int,
    plant_r: float,
    seed: int,
) -> tuple[SamplingFrame, ControlTruth]:
    """Deterministic control layout with a planted one-generation reproduction.

    Layout (closed-form): parent i is post i+1 authored by agent i in round 0; each
    parent gets `recipients_per_parent` single-pair strata at round 1 with certain
    selection; recipients are agents parent_count.., one per pair; the filler/organic
    author and the dedicated news user take the two ids past the recipients and join
    the exclusion registry. Every pair registers the uniform
    `q = plant_r / recipients_per_parent` and a FIXED potential response drawn on the
    dedicated response stream before any selection can occur.
    """
    parent_count = int(parent_count)
    recipients_per_parent = int(recipients_per_parent)
    if parent_count < 2 or recipients_per_parent < 1:
        raise ValueError("control frame needs >= 2 parents and >= 1 recipient per parent")
    response_probability = float(plant_r) / recipients_per_parent
    if not 0.0 <= response_probability <= 1.0 or not math.isfinite(response_probability):
        raise ValueError(
            f"response_probability = plant_r / recipients_per_parent must lie in "
            f"[0, 1], got {response_probability}")

    filler_author = parent_count + parent_count * recipients_per_parent
    news_user = filler_author + 1
    frame_id = f"frame:scripted-control:{int(seed)}"

    parent_records = tuple(
        ParentEligibility(
            parent_item_id=f"post:{i + 1}",
            author_agent_id=i,
            created_round=0,
        )
        for i in range(parent_count)
    )
    pairs = []
    for i in range(parent_count):
        for j in range(recipients_per_parent):
            agent_id = parent_count + i * recipients_per_parent + j
            pairs.append(CandidatePair(
                pair_id=f"pair:{i + 1}:{j + 1}",
                parent_item_id=f"post:{i + 1}",
                agent_id=agent_id,
                round_id=1,
                stratum_id=f"agent:{agent_id}:round:1",
                selection_probability=1.0,
                treatment_probability=0.5,
                parent_first_readable_round=1,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ))
    frame = SamplingFrame(
        frame_id=frame_id,
        parent_records=parent_records,
        excluded_recipient_agent_ids=tuple(range(parent_count)) + (filler_author, news_user),
        candidate_pairs=tuple(pairs),
    )
    validate_sampling_frame(frame)

    response_rng = np.random.default_rng(
        np.random.SeedSequence(int(seed), spawn_key=(CONTROL_RNG_STREAM_RESPONSES,))
    )
    potential = tuple(
        PotentialResponse(
            pair_id=pair.pair_id,
            response_probability=response_probability,
            potential_response=bool(response_rng.random() < response_probability),
        )
        for pair in frame.candidate_pairs
    )
    q_by_parent: dict[str, list[float]] = {}
    y_by_parent: dict[str, list[int]] = {}
    responses_by_pair = {row.pair_id: row for row in potential}
    for pair in frame.candidate_pairs:
        row = responses_by_pair[pair.pair_id]
        q_by_parent.setdefault(pair.parent_item_id, []).append(row.response_probability)
        y_by_parent.setdefault(pair.parent_item_id, []).append(int(row.potential_response))
    r_plant = math.fsum(
        math.fsum(q_by_parent[p.parent_item_id]) for p in parent_records
    ) / parent_count
    r_gen_frame = math.fsum(
        math.fsum(y_by_parent[p.parent_item_id]) for p in parent_records
    ) / parent_count
    truth = ControlTruth(
        frame_id=frame_id,
        r_plant=r_plant,
        r_gen_frame=r_gen_frame,
        potential_responses=potential,
    )
    return frame, truth


def scripted_action_for_assignment(
    assignment: Assignment,
    truth: ControlTruth,
):
    """Reply iff the assignment is treated AND its pair's fixed potential response is
    live. A holdout never replies — the potential response is realized only under
    actual service."""
    responses_by_pair = {row.pair_id: row for row in truth.potential_responses}
    row = responses_by_pair.get(assignment.pair_id)
    if row is None:
        raise ValueError(
            f"assignment names an unknown control pair: {assignment.pair_id!r}")
    if assignment.treated and row.potential_response:
        return ScriptedReply(
            assignment_id=assignment.assignment_id, pair_id=assignment.pair_id
        )
    return None


async def _drive_scripted_oasis_control(frame, truth, run_id, seed_stream_id, seed,
                                        database_path, expected_evidence_sha256):
    from oasis import ActionType, AgentGraph, SocialAgent, make
    from oasis.social_platform.channel import Channel
    from oasis.social_platform.platform import Platform
    from oasis.social_platform.typing import RecsysType

    from critaudit.sim.harness import harness_spec as hs
    from critaudit.sim.harness.causal_refresh import apply_causal_refresh
    from critaudit.sim.harness.oasis_adapter import (
        NEWS_AGENT_NAME,
        _causal_post_db_id,
        _make_news_sentinel_model,
        _new_user_info,
        collect_causal_outcomes,
        load_frame_eligibility_evidence,
        read_trace_rows,
    )

    validate_sampling_frame(frame)
    if truth.frame_id != frame.frame_id:
        raise ValueError("control truth does not belong to the supplied frame")
    selection_rng, treatment_rng = control_probe_rngs(seed_stream_id, seed)

    parent_count = len(frame.parent_records)
    recipients = sorted({pair.agent_id for pair in frame.candidate_pairs})
    # Registered convention: the exclusion registry's last two entries are the
    # filler/organic author and the dedicated news user.
    filler_author, news_user = frame.excluded_recipient_agent_ids[-2:]
    background_post_ids = (2 * parent_count + 1, 2 * parent_count + 2)

    sentinel = _make_news_sentinel_model(
        model_id="control-sentinel", endpoint_url="http://sentinel.invalid/v1",
        token="control", max_tokens=64, temperature=0.0, timeout=5,
        context_budget=1024)

    controller_box = []

    class _ScriptedControlPlatform(Platform):
        """Production refresh path with a deterministic fixture rec table."""

        async def refresh(self, agent_id):
            controller = controller_box[0] if controller_box else None
            return await apply_causal_refresh(
                super().refresh, self, controller, agent_id)

        async def update_rec_table(self):
            self.db_cursor.execute("DELETE FROM rec")
            for recipient in recipients:
                for post_id in background_post_ids:
                    self.db_cursor.execute(
                        "INSERT INTO rec VALUES (?, ?)", (recipient, post_id))
            self.db.commit()

    platform = _ScriptedControlPlatform(
        db_path=database_path,
        channel=Channel(),
        recsys_type=RecsysType(hs.RECSYS_TYPE),
        refresh_rec_post_count=3,
        max_rec_post_len=5,
        following_post_count=hs.FOLLOWING_POST_COUNT,
    )

    graph = AgentGraph()
    available = [ActionType(name) for name in
                 ("create_post", "create_comment", "repost", "quote_post", "do_nothing")]
    agent_names = {}
    for i in range(parent_count):
        agent_names[i] = f"control_author_{i}"
    for agent_id in recipients:
        agent_names[agent_id] = f"control_recipient_{agent_id}"
    agent_names[filler_author] = "control_organic"
    agent_names[news_user] = NEWS_AGENT_NAME
    for agent_id in sorted(agent_names):
        graph.add_agent(SocialAgent(
            agent_id=agent_id,
            user_info=_new_user_info(name=agent_names[agent_id], bio="control fixture",
                                     user_profile="control fixture"),
            model=sentinel, available_actions=available))

    env = make(agent_graph=graph, platform=platform, database_path=database_path)
    await env.reset()
    event_ids = []
    try:
        # round 0: parents by their registered authors, then fillers and background
        creations = []
        for i, parent in enumerate(frame.parent_records):
            creations.append((parent.author_agent_id, f"control parent {i + 1}"))
        for i in range(parent_count):
            creations.append((filler_author, f"control filler {i + 1}"))
        creations.append((filler_author, "control background one"))
        creations.append((filler_author, "control background two"))
        for expected_id, (agent_id, content) in enumerate(creations, start=1):
            result = await graph.get_agent(agent_id).env.action.create_post(content)
            if not (result.get("success") is True and result.get("post_id") == expected_id):
                raise RuntimeError(
                    f"scripted creation drifted from the registered layout: "
                    f"expected post {expected_id}, got {result!r}")
            event_ids.append(f"post:{expected_id}")

        await env.step({})  # -> round 1

        # eligibility evidence hash-verified BEFORE the first draw (the frame
        # bytes/hash on the returned run come from controller.frame_bytes below)
        evidence = load_frame_eligibility_evidence(
            frame, database_path, read_trace_rows(database_path))
        validate_frame_provenance(frame, evidence)
        evidence_bytes = frame_eligibility_evidence_to_bytes(evidence)
        evidence_sha = frame_eligibility_evidence_sha256(evidence)
        if expected_evidence_sha256 is not None and (
            evidence_sha != expected_evidence_sha256
        ):
            raise ValueError(
                f"pre-draw eligibility evidence hash {evidence_sha} does not "
                f"recreate the banked hash {expected_evidence_sha256} — "
                f"failing closed BEFORE the first draw")

        parent_posts = {}
        filler_posts = {}
        for i, parent in enumerate(frame.parent_records):
            parent_posts[parent.parent_item_id] = {
                "post_id": _causal_post_db_id(parent.parent_item_id),
                "user_id": parent.author_agent_id,
            }
            filler_posts[parent.parent_item_id] = {
                "post_id": parent_count + 1 + i,
                "user_id": filler_author,
            }
        controller = CausalRefreshController(
            frame, selection_rng, treatment_rng,
            parent_posts=parent_posts, filler_posts=filler_posts)
        controller_box.append(controller)

        for recipient in recipients:
            result = await graph.get_agent(recipient).env.action.refresh()
            if result.get("success") is not True:
                raise RuntimeError(f"control refresh failed: {result!r}")

        pairs_by_id = {pair.pair_id: pair for pair in frame.candidate_pairs}
        for assignment in controller.assignments:
            reply = scripted_action_for_assignment(assignment, truth)
            if reply is None:
                continue
            pair = pairs_by_id[assignment.pair_id]
            result = await graph.get_agent(pair.agent_id).env.action.create_comment(
                _causal_post_db_id(pair.parent_item_id),
                f"scripted reply {assignment.assignment_id}")
            if not (result.get("success") is True and "comment_id" in result):
                raise RuntimeError(f"scripted reply failed: {result!r}")
            event_ids.append(f"comment:{int(result['comment_id'])}")

        await env.step({})  # -> round 2, locking the outcome round
    finally:
        await env.close()

    # Mandatory run-boundary frame-integrity check (frame-integrity amendment):
    # the controller's private operational snapshot must still match its
    # construction-time canonical bytes BEFORE any outcome/artifact is produced.
    controller.assert_run_frame_intact()
    outcomes = collect_causal_outcomes(controller, database_path)
    manifest = ProbeManifest(
        run_id=run_id,
        frame_id=frame.frame_id,
        seed_stream_id=seed_stream_id,
        raw_seed=int(seed),
        root_ids=tuple(parent.parent_item_id for parent in frame.parent_records),
        round_ids=(0, 1),
        event_ids=tuple(event_ids),
        pair_ids=tuple(pair.pair_id for pair in frame.candidate_pairs),
        assignment_ids=tuple(a.assignment_id for a in controller.assignments),
    )
    return ScriptedControlRun(
        manifest=manifest,
        # immune canonical bytes/hash from the controller's private snapshot,
        # not a re-serialization of the caller's (mutable) frame object
        frame_bytes=controller.frame_bytes,
        frame_sha256=controller.frame_sha256,
        eligibility_evidence_bytes=evidence_bytes,
        eligibility_evidence_sha256=evidence_sha,
        draws=controller.draws,
        assignments=controller.assignments,
        outcomes=outcomes,
    )


def run_scripted_oasis_control(
    frame: SamplingFrame,
    truth: ControlTruth,
    run_id: str,
    seed_stream_id: str,
    seed: int,
    database_path: str,
    *,
    expected_evidence_sha256: str = None,
) -> ScriptedControlRun:
    """Full-platform non-LLM bridge: the exact production wrapper, selector, schema,
    estimator inputs, installed OASIS platform, round clock, and trace surface. The
    model wrapper is the fail-closed sentinel — any LLM invocation raises.

    `expected_evidence_sha256` (additive keyword, review F1): when supplied, the
    session's pre-draw eligibility-evidence hash must recreate it byte-identically
    or the session fails closed BEFORE its first draw."""
    import asyncio

    control_probe_rngs(seed_stream_id, seed)  # reject unregistered streams up front
    return asyncio.run(_drive_scripted_oasis_control(
        frame, truth, run_id, seed_stream_id, seed, database_path,
        expected_evidence_sha256))
