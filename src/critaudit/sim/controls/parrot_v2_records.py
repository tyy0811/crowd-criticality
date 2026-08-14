"""Task 5 (Branch-B parrot-null v2 implementation plan, 2026-07-31): the EMISSION-RECORD codec and
the ONE canonical served-set encoding.

Two independent byte surfaces live here, and nothing else does:

1. THE EMISSION RECORD — the canonical byte image of a replay's emitted content. It is what the
   width-invariance comparison is taken over (spec rev-5 §4: the null's claim is that the crowd's
   emission stream is byte-identical across recommender widths), so it must be a function of the
   emissions ALONE: a canonical serialization of every `EventRecord` the Task-1 loader read back out
   of the replay database, with ALL SIX fields (`item_id`, `time`, `agent_id`, `parent_item_id`,
   `content`, `seq`) — no projection, no rounding, no field subset that could hide a divergence.
   Records are ordered by `(time, seq)`: `time` is the round-granular clock and `seq` is the trace
   rowid, the same (primary, tiebreaker) order the harness's own pairing uses, so the ordering is a
   property of the data rather than of the reader's iteration.

   `decode_emission_record` is the SINGLE decode point for that image (Tasks 6-7 never parse the
   base64 themselves). It is fail-closed on byte identity: the reconstructed tuple is re-encoded and
   must reproduce the decoded bytes EXACTLY, so JSON-equivalent-but-non-canonical bytes are rejected
   rather than silently normalized — a comparison of two encodings can never be laundered through a
   re-serialization that differs from what the producer actually wrote.

2. THE SERVED-SET ENCODING — `canonical_served_encoding` is THE one encoding of a served item-id set
   (sorted, compact separators, NO trailing newline; the empty set is exactly `b"[]"`), and
   `served_hash` its SHA-256 hexdigest. The violator arm's whole contract is that its extra post's
   content is that hash (rev-2 blocker 5), and the ledger cross-check re-derives it from the recorded
   `served_item_ids`; a second encoding anywhere would make the two silently incomparable, so there is
   exactly one, here.

The emission record follows the run-codec house pattern (`causal_probe_records.py`,
`parrot_v2_profile.py`, `parrot_v2_schedule.py`): sorted keys, `(",", ":")` separators, trailing
newline, byte-identity re-encode on reconstruction. The served encoding deliberately does NOT carry
the trailing newline — it is a hash INPUT, not a stored artifact, and its bytes are pinned by the
brief's literal `b"[]"`.
"""
from __future__ import annotations

import base64
import hashlib
import json

from critaudit.sim.harness.types import EventRecord

__all__ = [
    "EMISSION_RECORD_FIELDS",
    "emission_record_bytes",
    "encode_emission_record",
    "decode_emission_record",
    "canonical_served_encoding",
    "served_hash",
]

# The FULL EventRecord field set the emission record serializes. A field added to EventRecord
# without being added here would silently drop out of the invariance comparison, so the tuple is
# asserted against the dataclass at import time (the structural-firewall habit of
# parrot_v2_profile.py / parrot_v2_schedule.py).
EMISSION_RECORD_FIELDS = ("item_id", "time", "agent_id", "parent_item_id", "content", "seq")
assert tuple(EventRecord.__dataclass_fields__) == EMISSION_RECORD_FIELDS


def _canonical_json_bytes(payload) -> bytes:
    return (
        json.dumps(payload, allow_nan=False, ensure_ascii=False, separators=(",", ":"),
                   sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _event_payload(event) -> dict:
    if type(event) is not EventRecord:
        raise TypeError("every emission must be exactly EventRecord")
    return {
        "item_id": event.item_id,
        "time": event.time,
        "agent_id": event.agent_id,
        "parent_item_id": event.parent_item_id,
        "content": event.content,
        "seq": event.seq,
    }


def emission_record_bytes(events) -> bytes:
    """The canonical byte image of a replay's emissions: every EventRecord, ALL SIX fields, ordered
    by `(time, seq)` (round-granular clock primary, trace rowid tiebreaker). Sorting here rather
    than trusting the caller's order makes the image a function of the data alone."""
    ordered = sorted(events, key=lambda e: (e.time, e.seq))
    return _canonical_json_bytes([_event_payload(e) for e in ordered])


def encode_emission_record(events) -> str:
    """`emission_record_bytes` in base64 (ASCII) — the transport form carried in a replay payload's
    `emission_record_b64`. Exact inverse of `decode_emission_record`."""
    return base64.b64encode(emission_record_bytes(events)).decode("ascii")


def decode_emission_record(b64) -> tuple:
    """THE single decode point for an emission record (Tasks 6-7 never parse the base64 themselves).

    Fail-closed on every count: the base64 must decode, the bytes must be valid JSON of the pinned
    shape, and the reconstructed tuple must RE-ENCODE to the decoded bytes byte-for-byte — so a
    non-canonically-ordered or non-canonically-formatted record is rejected rather than normalized
    into an image that was never actually produced."""
    if isinstance(b64, str):
        b64 = b64.encode("ascii")
    try:
        data = base64.b64decode(b64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"emission record is not valid base64: {exc}")
    try:
        payload = json.loads(data)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError(f"emission record bytes are not valid JSON: {exc}")
    if not isinstance(payload, list):
        raise ValueError("emission record bytes have a drifted schema: payload is not an array")
    try:
        events = tuple(
            EventRecord(
                item_id=row["item_id"],
                time=row["time"],
                agent_id=row["agent_id"],
                parent_item_id=row["parent_item_id"],
                content=row["content"],
                seq=row["seq"])
            for row in payload)
    except (KeyError, TypeError) as exc:
        raise ValueError(f"emission record bytes have a drifted schema: {exc}")
    if emission_record_bytes(events) != data:
        raise ValueError("emission record bytes are not canonical (fail-closed)")
    return events


def canonical_served_encoding(item_ids) -> bytes:
    """THE one encoding of a served item-id SET: sorted, compact separators, no trailing newline.
    The empty set is exactly `b"[]"`. This is a hash input, never a stored artifact."""
    return json.dumps(sorted(item_ids), separators=(",", ":")).encode()


def served_hash(item_ids) -> str:
    """SHA-256 hexdigest of `canonical_served_encoding(item_ids)` — the violator arm's post
    content, and what the ledger cross-check re-derives from the recorded served set."""
    return hashlib.sha256(canonical_served_encoding(item_ids)).hexdigest()
