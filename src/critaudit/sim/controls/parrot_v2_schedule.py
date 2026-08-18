"""Task 4 (Branch-B parrot-null v2 implementation plan, 2026-07-31): the KNOB-INDEPENDENT
schedule generator + `ScheduleEnvelope`.

A schedule is the complete, width-independent action script for one replay: which agent acts, in
which round, with which action kind, against which target, carrying which text. It is generated
ONCE per `schedule_seed` from ONE registered cohort window's `CohortActionProfile` (Task 3) and is
then replayed unchanged at every recommender width — that is the whole point of the matched null:
the ONLY thing that varies across the width arm is the platform's recommender, never the crowd's
action script. Nothing in this module reads a width, a recommender setting, or any replay output.

REPOSTS ARE VALID TARGETS. OASIS's own duplicate-repost predicate is therefore live in two clauses,
and this module mirrors platform.py's written `original_post_id` bookkeeping exactly (the table is
pinned executably by Task 0's `tests/test_parrot_v2_substrate.py::test_written_original_resolution`):

    stored_original(create_post) = stored_original(news_post) = None
    stored_original(repost of x) = stored_original(x) if x.kind == "repost" else index(x)
    stored_original(quote  of x) = index(x) if x.kind in ("create_post", "news_post")
                                            else stored_original(x)
    written[a] = { stored_original(e) : e is a PRIOR scheduled repost OR quote by agent a }

    a repost of candidate t by agent a is EXCLUDED iff
        index(t) in written[a]                                            (clause 1)
        or (t.kind == "repost" and stored_original(t) in written[a])      (clause 2)

Clause 1 covers prior QUOTES by construction (a quote writes an `original_post_id` too, so it lands
in `written[a]` exactly like a repost does); clause 2 is the root-resolution clause that OASIS
applies when the candidate is itself a repost. Both fire on real candidates in a generated schedule
because reposts are in the target pool. A slot whose action-valid set is EMPTY is a hard
`ValueError` HERE, at generation — the replay is never reached, so a schedule that OASIS would
reject can never be handed to the platform in the first place (fail-closed, rule 5).

DRAW DISCIPLINE (the reproducibility contract — a schedule must be re-derivable from this text
alone, so it is spelled out rather than left to the code).

Five independent `numpy` Generators are created ONCE per `build_schedule_envelope` call, via
`parrot_v2_spec.v2_rng(schedule_seed, STREAM_*)` — one each for STREAM_CONTENT, STREAM_TYPE,
STREAM_AGENT, STREAM_TARGET, STREAM_REFRESH. (STREAM_PLATFORM is not drawn here; it is consumed by
`parrot_v2_spec.platform_seed`.) EVERY draw in this module is an INTEGER INDEX draw of the form
`int(rng.integers(0, n))` — uniform over 0..n-1, half-open. No floats, no `shuffle`, no
`permutation`, no `choice`: the stream position after k draws is a function of k alone, so stream
consumption is slot-deterministic and knob-free.

Rounds run r = 0 .. len(profile.per_round_type_counts) - 1. WITHIN each round r, in this exact
order:

  A. REFRESH BLOCK, first. `per_round_refresh_counts[r]` refresh actions, in generated order; each
     consumes exactly ONE draw on STREAM_REFRESH for its agent, uniform over the crowd ids
     0..N_CROWD_AGENTS-1 (0..49 at the frozen operating point). A refresh carries no target, no
     content and no emission index.

  B. ALL `create_post` SLOTS, next (`per_round_type_counts[r][0]` of them, generated order). Each
     consumes, IN THIS ORDER: one agent draw on STREAM_AGENT, then one content draw on
     STREAM_CONTENT (uniform WITH replacement over `profile.authored_corpus`). No target draw.

  C. TYPE ORDER for the round's REMAINING multiset. The remaining counts
     (`create_comment` x counts[1], `repost` x counts[2], `quote_post` x counts[3]) are laid out in
     the fixed pool order `ACTION_TYPES[1:]` and then ORDERED by m = counts[1]+counts[2]+counts[3]
     sequential WITHOUT-replacement index draws on STREAM_TYPE: draw `j = int(rng.integers(0,
     len(pool)))` and pop `pool[j]`, m times. All m draws for the round are taken BEFORE any of the
     round's remaining slots is emitted.

  D. THE REMAINING SLOTS, in the order drawn in C. Each consumes, IN THIS ORDER:
       1. one agent draw on STREAM_AGENT (uniform over 0..N_CROWD_AGENTS-1);
       2. one target draw on STREAM_TARGET — the candidate list is the emission indices of ALL
          PRIOR post-type emissions (kinds `create_post`, `quote_post`, `repost`, `news_post`;
          comments are never targets), ascending. A `create_comment` or `quote_post` slot draws
          uniformly over that UNFILTERED list; a `repost` slot's list is FILTERED FIRST by
          `repost_target_valid` and the draw is uniform over the SURVIVORS. Empty either way ->
          ValueError (rule 5);
       3. content — one draw on STREAM_CONTENT for `create_comment` / `quote_post`; a `repost`
          slot consumes NO content draw and carries the literal `""`.

  E. NEWS SLOTS, LAST in the round: every `(round, content)` entry of `profile.news_events` whose
     round == r, in profile order. A news slot consumes NO draw AT ALL — not agent, not content:
     its agent is the dedicated news user `NEWS_USER_AGENT_ID` (50) and its content is the profile's
     verbatim news text. (`per_round_type_counts` is news-ADJUSTED by Task 3, so a news event is not
     also counted as a crowd `create_post`.)

`emission_index` is assigned sequentially 0, 1, 2, ... over the NON-refresh actions in action
order; refresh actions carry `None`. `target_ref` is an emission index, never a platform id.

The envelope codec follows the run-codec house pattern (`causal_probe_records.py`,
`parrot_v2_profile.py`): sorted keys, `(",", ":")` separators, trailing newline, byte-identity
re-encode on reconstruction. `schedule_sha256` is the SHA-256 of the canonical serialization of ALL
OTHER envelope fields — non-circular by construction — and `envelope_from_bytes` RECOMPUTES it and
rejects a mismatch, so a tampered field cannot ride in behind a stale-but-canonical digest.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields

import critaudit.sim.controls.parrot_v2_spec as parrot_v2_spec
from critaudit.sim.controls.parrot_v2_profile import ACTION_TYPES, profile_sha256
from critaudit.sim.harness.harness_spec import NEWS_USER_AGENT_ID, OPERATING_POINT

__all__ = [
    "ScheduleAction",
    "ScheduleEnvelope",
    "SCHEDULE_ACTION_FIELDS",
    "SCHEDULE_ENVELOPE_FIELDS",
    "POST_KINDS",
    "N_CROWD_AGENTS",
    "stored_original",
    "repost_target_valid",
    "build_schedule_envelope",
    "envelope_to_bytes",
    "envelope_sha256",
    "envelope_from_bytes",
]

# The crowd ids a scheduled agent draw may land on: 0..N_CROWD_AGENTS-1 (0..49 at the frozen
# operating point). The news user sits one past the last crowd id and is NEVER drawn.
N_CROWD_AGENTS = OPERATING_POINT["n_agents"]
assert NEWS_USER_AGENT_ID == N_CROWD_AGENTS   # harness_spec's own rule: id = n_agents

# Post-type emissions: the ONLY legal targets (the signed spec's post-type set — comments are never
# targets, and reposts ARE targets, which is what keeps predicate clause 2 live).
POST_KINDS = ("create_post", "quote_post", "repost", "news_post")
# Kinds that write an `original_post_id` row (i.e. that have a stored original at all).
_DERIVED_KINDS = ("repost", "quote_post")
# Kinds a quote resolves to ITSELF rather than root-resolving through.
_ROOT_KINDS = ("create_post", "news_post")
# The crowd emission kinds that consume a content draw from the authored corpus.
_BOOTSTRAP_KINDS = ("create_post", "create_comment", "quote_post")


@dataclass(frozen=True)
class ScheduleAction:
    """One scheduled action. `target_ref` is an EMISSION INDEX (never a platform post/comment id)
    and is None for refresh/create_post/news_post; `content` is None for refresh, the literal ""
    for repost, and authored/news text otherwise; `emission_index` is None for refresh and
    sequential over the non-refresh actions otherwise."""
    round: int
    kind: str
    agent_id: int
    target_ref: int | None
    content: str | None
    emission_index: int | None


@dataclass(frozen=True)
class ScheduleEnvelope:
    """The complete replayable schedule for one `schedule_seed`, plus its identity fields.

    `schedule_sha256` is the SHA-256 of the canonical serialization of all the OTHER fields, so the
    digest is well-defined without self-reference and can be recomputed on load."""
    schema: int
    schedule_seed: int
    assigned_window: int
    profile_sha256: str
    platform_seed: int
    actions: tuple
    schedule_sha256: str


# Field-set pins (the structural-firewall habit of parrot_v2_profile.py / cohort_marginals.py): a
# field added or reordered here is a SPEC CHANGE and must break loudly, because both the canonical
# serialization below and the digest it feeds are field-set-defined.
SCHEDULE_ACTION_FIELDS = (
    "round", "kind", "agent_id", "target_ref", "content", "emission_index")
SCHEDULE_ENVELOPE_FIELDS = (
    "schema", "schedule_seed", "assigned_window", "profile_sha256", "platform_seed",
    "actions", "schedule_sha256")
assert tuple(f.name for f in fields(ScheduleAction)) == SCHEDULE_ACTION_FIELDS
assert tuple(f.name for f in fields(ScheduleEnvelope)) == SCHEDULE_ENVELOPE_FIELDS


# --- written-original bookkeeping (mirrors platform.py; pinned by Task 0's
#     test_written_original_resolution) ---------------------------------------------------------

def stored_original(emissions, idx):
    """The `original_post_id` platform.py would write for emission `idx`, or None if that emission
    writes none (`create_post` / `news_post` / `create_comment`).

    `emissions` is the LIST of emission actions indexed by `emission_index` (index i is the action
    whose `emission_index == i`); `idx` is an emission index. Resolution is iterative rather than
    recursive so a long repost chain can never hit the interpreter's recursion limit:

      - repost of x -> stored_original(x) if x is itself a repost, else index(x);
      - quote  of x -> index(x) if x is a create_post/news_post, else stored_original(x).

    Every walk terminates at a target that is not root-resolved-through; a cyclic chain (impossible
    by construction, since a target always precedes its emitter) fails closed."""
    if emissions[idx].kind not in _DERIVED_KINDS:
        return None
    cur = int(idx)
    seen = set()
    while True:
        if cur in seen:
            raise ValueError(
                f"stored_original: repost/quote chain from emission {idx} is cyclic (fail-closed)")
        seen.add(cur)
        action = emissions[cur]
        target_idx = action.target_ref
        if target_idx is None:
            raise ValueError(
                f"stored_original: {action.kind} emission {cur} has no target_ref (fail-closed)")
        target_idx = int(target_idx)
        target = emissions[target_idx]
        if action.kind == "repost":
            if target.kind != "repost":
                return target_idx           # repost of a common/quote target -> the target itself
        elif target.kind in _ROOT_KINDS:
            return target_idx               # quote of a common target -> the target itself
        # otherwise: root-resolve THROUGH the target, using the target's own rule
        if target.kind not in _DERIVED_KINDS:
            raise ValueError(
                f"stored_original: emission {cur} ({action.kind}) targets emission {target_idx} of "
                f"kind {target.kind!r}, which writes no original (fail-closed)")
        cur = target_idx


def repost_target_valid(emissions, written, agent_id, candidate_idx):
    """Whether agent `agent_id` may repost emission `candidate_idx` — OASIS's duplicate-repost
    predicate, both clauses. `written` maps agent_id -> set of that agent's already-written
    `stored_original` values (from its PRIOR reposts AND quotes); a missing/empty entry means the
    agent has written none, so every candidate survives.

    EXCLUDED iff `candidate_idx in written[agent_id]` (clause 1 — prior QUOTES are in `written` by
    construction, so a prior quote of t blocks a repost of t) OR the candidate is itself a repost
    whose stored original is in `written[agent_id]` (clause 2 — root resolution)."""
    prior = written.get(agent_id)
    if not prior:
        return True
    candidate_idx = int(candidate_idx)
    if candidate_idx in prior:                                          # clause 1
        return False
    candidate = emissions[candidate_idx]
    if candidate.kind == "repost" and stored_original(emissions, candidate_idx) in prior:
        return False                                                    # clause 2
    return True


# --- generation -------------------------------------------------------------------------------

def _count(value, *, what):
    n = int(value)
    if n != value or n < 0:
        raise ValueError(f"build_schedule_envelope: {what} must be a non-negative integer, got "
                         f"{value!r} (fail-closed)")
    return n


def _draw_index(rng, n):
    """The ONE draw primitive: a uniform integer index over 0..n-1 (see the module docstring's draw
    discipline). Never called with n <= 0 — callers fail closed on an empty set first."""
    return int(rng.integers(0, n))


def build_schedule_envelope(profile, schedule_seed) -> ScheduleEnvelope:
    """Generate the knob-independent schedule for `schedule_seed` from one window's action profile.

    Fails closed unless `parrot_v2_spec.assigned_window(schedule_seed)` is the profile's own
    window: a schedule seed is bound to exactly one registered cohort window by the round-robin,
    and generating against a different window would silently cross the matched-null pairing."""
    schedule_seed = int(schedule_seed)
    window = parrot_v2_spec.assigned_window(schedule_seed)
    if window != profile.window_seed:
        raise ValueError(
            f"build_schedule_envelope: schedule seed {schedule_seed} is assigned window {window}, "
            f"but the profile's window is {profile.window_seed} (fail-closed)")

    profile_sha = profile_sha256(profile)       # also pins profile to be exactly CohortActionProfile
    n_rounds = len(profile.per_round_type_counts)
    if len(profile.per_round_refresh_counts) != n_rounds:
        raise ValueError(
            f"build_schedule_envelope: profile has {n_rounds} rounds of type counts but "
            f"{len(profile.per_round_refresh_counts)} of refresh counts (fail-closed)")

    corpus = tuple(profile.authored_corpus)
    news_by_round = {}
    for entry in profile.news_events:
        rnd, content = entry
        news_by_round.setdefault(int(rnd), []).append(content)
    stray = sorted(r for r in news_by_round if not 0 <= r < n_rounds)
    if stray:
        raise ValueError(
            f"build_schedule_envelope: news events in round(s) {stray} outside the profile's "
            f"{n_rounds} rounds (fail-closed)")

    rng_content = parrot_v2_spec.v2_rng(schedule_seed, parrot_v2_spec.STREAM_CONTENT)
    rng_type = parrot_v2_spec.v2_rng(schedule_seed, parrot_v2_spec.STREAM_TYPE)
    rng_agent = parrot_v2_spec.v2_rng(schedule_seed, parrot_v2_spec.STREAM_AGENT)
    rng_target = parrot_v2_spec.v2_rng(schedule_seed, parrot_v2_spec.STREAM_TARGET)
    rng_refresh = parrot_v2_spec.v2_rng(schedule_seed, parrot_v2_spec.STREAM_REFRESH)

    actions = []
    emissions = []      # emission actions, list index == emission_index
    written = {}        # agent_id -> set of stored_original values already written by that agent

    def _content_for(kind, rnd):
        if not corpus:
            raise ValueError(
                f"build_schedule_envelope: round {rnd} {kind} slot needs authored content but the "
                f"profile's authored_corpus is empty — fail-closed at schedule generation")
        return corpus[_draw_index(rng_content, len(corpus))]

    def _target_for(kind, agent, rnd):
        pool = [e.emission_index for e in emissions if e.kind in POST_KINDS]
        if kind == "repost":
            pool = [i for i in pool if repost_target_valid(emissions, written, agent, i)]
        if not pool:
            raise ValueError(
                f"build_schedule_envelope: round {rnd} {kind} slot for agent {agent} has an empty "
                f"action-valid target set — fail-closed at schedule generation")
        return int(pool[_draw_index(rng_target, len(pool))])

    def _emit(action):
        actions.append(action)
        emissions.append(action)
        if action.kind in _DERIVED_KINDS:
            written.setdefault(action.agent_id, set()).add(
                stored_original(emissions, action.emission_index))

    for rnd in range(n_rounds):
        counts = profile.per_round_type_counts[rnd]
        if len(counts) != len(ACTION_TYPES):
            raise ValueError(
                f"build_schedule_envelope: round {rnd} type counts {counts!r} do not match the "
                f"{len(ACTION_TYPES)} action types {ACTION_TYPES!r} (fail-closed)")

        # A. refresh block, first
        for _ in range(_count(profile.per_round_refresh_counts[rnd], what=f"round {rnd} refresh count")):
            actions.append(ScheduleAction(
                round=rnd, kind="refresh", agent_id=_draw_index(rng_refresh, N_CROWD_AGENTS),
                target_ref=None, content=None, emission_index=None))

        # B. all create_post slots, next
        for _ in range(_count(counts[0], what=f"round {rnd} create_post count")):
            agent = _draw_index(rng_agent, N_CROWD_AGENTS)
            _emit(ScheduleAction(
                round=rnd, kind="create_post", agent_id=agent, target_ref=None,
                content=_content_for("create_post", rnd), emission_index=len(emissions)))

        # C. the remaining type multiset, ordered by without-replacement index draws on STREAM_TYPE
        pool = []
        for offset, kind in enumerate(ACTION_TYPES[1:], start=1):
            pool.extend([kind] * _count(counts[offset], what=f"round {rnd} {kind} count"))
        order = []
        while pool:
            order.append(pool.pop(_draw_index(rng_type, len(pool))))

        # D. the remaining slots, in that order
        for kind in order:
            agent = _draw_index(rng_agent, N_CROWD_AGENTS)
            target_ref = _target_for(kind, agent, rnd)
            content = "" if kind == "repost" else _content_for(kind, rnd)
            _emit(ScheduleAction(
                round=rnd, kind=kind, agent_id=agent, target_ref=target_ref,
                content=content, emission_index=len(emissions)))

        # E. news slots, LAST in the round; no draws at all
        for content in news_by_round.get(rnd, ()):
            _emit(ScheduleAction(
                round=rnd, kind="news_post", agent_id=NEWS_USER_AGENT_ID, target_ref=None,
                content=content, emission_index=len(emissions)))

    actions = tuple(actions)
    fields_but_digest = dict(
        schema=parrot_v2_spec.SCHEMA,
        schedule_seed=schedule_seed,
        assigned_window=window,
        profile_sha=profile_sha,
        platform_seed=parrot_v2_spec.platform_seed(schedule_seed),
        actions=actions)
    return ScheduleEnvelope(
        schema=fields_but_digest["schema"],
        schedule_seed=fields_but_digest["schedule_seed"],
        assigned_window=fields_but_digest["assigned_window"],
        profile_sha256=fields_but_digest["profile_sha"],
        platform_seed=fields_but_digest["platform_seed"],
        actions=fields_but_digest["actions"],
        schedule_sha256=_schedule_digest(**fields_but_digest),
    )


# --- canonical codec (run-codec house pattern: sorted keys, compact separators, trailing newline,
#     byte-identity re-encode on reconstruction — plus the RECOMPUTED schedule_sha256) -----------

def _canonical_json_bytes(payload) -> bytes:
    return (
        json.dumps(payload, allow_nan=False, ensure_ascii=False, separators=(",", ":"),
                   sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _action_payload(action) -> dict:
    if type(action) is not ScheduleAction:
        raise TypeError("every schedule action must be exactly ScheduleAction")
    return {
        "round": action.round,
        "kind": action.kind,
        "agent_id": action.agent_id,
        "target_ref": action.target_ref,
        "content": action.content,
        "emission_index": action.emission_index,
    }


def _digest_payload(*, schema, schedule_seed, assigned_window, profile_sha, platform_seed,
                    actions) -> dict:
    """The canonical payload of ALL envelope fields EXCEPT `schedule_sha256` — what the digest is
    taken over, so the digest is non-circular."""
    return {
        "schema": schema,
        "schedule_seed": schedule_seed,
        "assigned_window": assigned_window,
        "profile_sha256": profile_sha,
        "platform_seed": platform_seed,
        "actions": [_action_payload(a) for a in actions],
    }


def _schedule_digest(**kwargs) -> str:
    return hashlib.sha256(_canonical_json_bytes(_digest_payload(**kwargs))).hexdigest()


def envelope_to_bytes(envelope: ScheduleEnvelope) -> bytes:
    if type(envelope) is not ScheduleEnvelope:
        raise TypeError("envelope must be exactly ScheduleEnvelope")
    payload = _digest_payload(
        schema=envelope.schema,
        schedule_seed=envelope.schedule_seed,
        assigned_window=envelope.assigned_window,
        profile_sha=envelope.profile_sha256,
        platform_seed=envelope.platform_seed,
        actions=envelope.actions)
    payload["schedule_sha256"] = envelope.schedule_sha256
    return _canonical_json_bytes(payload)


def envelope_sha256(envelope: ScheduleEnvelope) -> str:
    return hashlib.sha256(envelope_to_bytes(envelope)).hexdigest()


def envelope_from_bytes(data: bytes) -> ScheduleEnvelope:
    """Rebuild a ScheduleEnvelope from its canonical bytes, fail-closed on every count:

    1. the bytes must be valid JSON;
    2. `schema` must be the spec's current SCHEMA (no silent cross-schema load);
    3. the reconstruction must re-encode to the input BYTE-FOR-BYTE — JSON-equivalent but
       non-canonical bytes are rejected rather than normalized, so a hash chain cannot be laundered
       through re-serialization;
    4. the RECOMPUTED `schedule_sha256` must equal the stored one — a stored digest is never
       trusted, so a tampered field cannot ride in behind a canonical-but-stale digest."""
    try:
        payload = json.loads(data)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError(f"schedule envelope bytes are not valid JSON: {exc}")
    if not isinstance(payload, dict):
        raise ValueError("schedule envelope bytes have a drifted schema: payload is not an object")
    if payload.get("schema") != parrot_v2_spec.SCHEMA:
        raise ValueError(
            f"schedule envelope schema {payload.get('schema')!r} is not the spec's "
            f"{parrot_v2_spec.SCHEMA} (fail-closed)")
    try:
        envelope = ScheduleEnvelope(
            schema=payload["schema"],
            schedule_seed=payload["schedule_seed"],
            assigned_window=payload["assigned_window"],
            profile_sha256=payload["profile_sha256"],
            platform_seed=payload["platform_seed"],
            actions=tuple(
                ScheduleAction(
                    round=row["round"],
                    kind=row["kind"],
                    agent_id=row["agent_id"],
                    target_ref=row["target_ref"],
                    content=row["content"],
                    emission_index=row["emission_index"])
                for row in payload["actions"]),
            schedule_sha256=payload["schedule_sha256"],
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"schedule envelope bytes have a drifted schema: {exc}")
    if envelope_to_bytes(envelope) != data:
        raise ValueError("schedule envelope bytes are not canonical (fail-closed)")
    recomputed = _schedule_digest(
        schema=envelope.schema,
        schedule_seed=envelope.schedule_seed,
        assigned_window=envelope.assigned_window,
        profile_sha=envelope.profile_sha256,
        platform_seed=envelope.platform_seed,
        actions=envelope.actions)
    if recomputed != envelope.schedule_sha256:
        raise ValueError(
            f"schedule envelope schedule_sha256 {envelope.schedule_sha256!r} does not match the "
            f"recomputed {recomputed!r} (fail-closed)")
    return envelope
