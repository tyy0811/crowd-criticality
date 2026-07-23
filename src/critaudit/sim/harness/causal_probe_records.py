"""Immutable structural records for the causal reply probe."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

__all__ = (
    "ParentEligibility",
    "CandidatePair",
    "SamplingFrame",
    "PairEligibilityEvidence",
    "FrameEligibilityEvidence",
    "StratumDraw",
    "Assignment",
    "Outcome",
    "ProbeManifest",
    "RReplyEstimate",
    "sampling_frame_to_bytes",
    "sampling_frame_sha256",
    "sampling_frame_from_bytes",
    "frame_eligibility_evidence_to_bytes",
    "frame_eligibility_evidence_sha256",
)


@dataclass(frozen=True)
class ParentEligibility:
    parent_item_id: str
    author_agent_id: int
    created_round: int


@dataclass(frozen=True)
class CandidatePair:
    pair_id: str
    parent_item_id: str
    agent_id: int
    round_id: int
    stratum_id: str
    selection_probability: float
    treatment_probability: float
    parent_first_readable_round: int
    prior_exposure_count: int
    complete_same_action_opportunity: bool


@dataclass(frozen=True)
class SamplingFrame:
    frame_id: str
    parent_records: tuple[ParentEligibility, ...]
    excluded_recipient_agent_ids: tuple[int, ...]
    candidate_pairs: tuple[CandidatePair, ...]


@dataclass(frozen=True)
class PairEligibilityEvidence:
    pair_id: str
    parent_author_agent_id: int
    parent_created_round: int
    first_readable_round: int
    prior_exposure_count: int
    complete_same_action_opportunity: bool


@dataclass(frozen=True)
class FrameEligibilityEvidence:
    frame_id: str
    news_user_agent_id: int
    pair_evidence: tuple[PairEligibilityEvidence, ...]


@dataclass(frozen=True)
class StratumDraw:
    frame_id: str
    stratum_id: str
    selected_pair_id: str | None


@dataclass(frozen=True)
class Assignment:
    assignment_id: str
    frame_id: str
    pair_id: str
    filler_item_id: str
    treated: bool


@dataclass(frozen=True)
class Outcome:
    assignment_id: str
    parent_served: bool
    parent_seen_in_background: bool
    feed_length_before: int
    feed_length_after: int
    direct_child_item_id: str | None
    direct_child_parent_id: str | None
    child_author_agent_id: int | None
    child_round: int | None


@dataclass(frozen=True)
class ProbeManifest:
    run_id: str
    frame_id: str
    seed_stream_id: str
    raw_seed: int
    root_ids: tuple[str, ...]
    round_ids: tuple[int, ...]
    event_ids: tuple[str, ...]
    pair_ids: tuple[str, ...]
    assignment_ids: tuple[str, ...]


@dataclass(frozen=True)
class RReplyEstimate:
    frame_id: str
    estimate: float
    estimated_diagonal_variance_bound: float
    standard_error_conservative: float
    ci95_low: float
    ci95_high: float
    deterministic_worst_case_variance_bound: float
    parent_count: int
    candidate_pair_count: int
    stratum_count: int
    draw_count: int
    selected_count: int
    no_selection_count: int
    treated_count: int
    control_count: int
    response_count: int
    status: str


def _canonical_json_bytes(record: object) -> bytes:
    return (
        json.dumps(
            asdict(record),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sampling_frame_to_bytes(frame: SamplingFrame) -> bytes:
    if type(frame) is not SamplingFrame:
        raise TypeError("frame must be exactly SamplingFrame")
    return _canonical_json_bytes(frame)


def sampling_frame_sha256(frame: SamplingFrame) -> str:
    return hashlib.sha256(sampling_frame_to_bytes(frame)).hexdigest()


def sampling_frame_from_bytes(data: bytes) -> SamplingFrame:
    """Rebuild a SamplingFrame from its canonical bytes, fail-closed.

    The reconstruction must reproduce the input byte-for-byte — JSON-equivalent
    but non-canonical bytes are rejected rather than silently normalized, so a
    frame's hash chain cannot be laundered through re-serialization."""
    try:
        payload = json.loads(data)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError(f"sampling frame bytes are not valid JSON: {exc}")
    try:
        frame = SamplingFrame(
            frame_id=payload["frame_id"],
            parent_records=tuple(
                ParentEligibility(**row) for row in payload["parent_records"]),
            excluded_recipient_agent_ids=tuple(
                payload["excluded_recipient_agent_ids"]),
            candidate_pairs=tuple(
                CandidatePair(**row) for row in payload["candidate_pairs"]),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"sampling frame bytes have a drifted schema: {exc}")
    if sampling_frame_to_bytes(frame) != data:
        raise ValueError(
            "sampling frame bytes are not canonical (fail-closed)")
    return frame


def frame_eligibility_evidence_to_bytes(
    evidence: FrameEligibilityEvidence,
) -> bytes:
    if type(evidence) is not FrameEligibilityEvidence:
        raise TypeError("evidence must be exactly FrameEligibilityEvidence")
    return _canonical_json_bytes(evidence)


def frame_eligibility_evidence_sha256(
    evidence: FrameEligibilityEvidence,
) -> str:
    return hashlib.sha256(
        frame_eligibility_evidence_to_bytes(evidence)
    ).hexdigest()
