"""Task 5 (Branch-B parrot-null v2 implementation plan, 2026-07-31): the SERIAL DETERMINISTIC
REPLAYER — the one place a parrot-v2 schedule actually touches the installed OASIS platform.

WHAT THIS IS. `replay_envelope` takes ONE `ScheduleEnvelope` (Task 4: the knob-independent action
script) and ONE recommender width, and drives the real platform through that script exactly once.
Nothing about the crowd's behaviour is decided here: every agent, action kind, target and text was
fixed at schedule generation, and the ONLY thing that varies across the width arm is the platform's
own recommender. That is the matched null's entire design — so this module's job is to be a faithful,
fail-closed executor, never a source of decisions.

WHY THE PROTOCOL IS FROZEN (spec rev-5 §3b). `env.step()` is NEVER called. `env.step` fans the
round's actions out through `asyncio.gather` (env.py:192-193), which makes both the platform-side
write order and the trace rowids a race — and the trace rowid is the `seq` field of every emitted
record, i.e. part of the byte image the invariance comparison is taken over. A concurrent round would
therefore inject a source of cross-width divergence that has nothing to do with the recommender. The
round loop below issues each action SERIALLY, in schedule order, and ticks the clock itself
(`env.step`'s only other duty at the Twitter platform type, env.py:197-198), asserting the clock
before and after so a silent tick drift can never accumulate. Actions go through the AGENT action
path (`graph.get_agent(id).env.action.*`, the two-arg signatures of agent_action.py:145/509/192/166/97
— NOT the platform's one-tuple signatures), which is the same path OASIS's own manual/LLM actions
funnel into, so the platform sees ordinary traffic.

CONSTRUCTION MIRRORS THE REGISTERED COHORT DRIVER (`oasis_adapter._run_oasis_minimal_async`): the
same stock `Channel()`, the same `Platform` ctor arguments (with `refresh_rec_post_count` = the
replay's width and `max_rec_post_len` = `parrot_v2_spec.MAX_REC_POST_LEN`), the same 50 crowd agents
+ dedicated news user 50, the same `make(...)` / `await env.reset()` order, and the same follow-edge
realization loop over `build_follow_edges(...)` in drawn order. The two DELIBERATE differences are
both fail-closed narrowings rather than widenings:
  - EVERY agent (not just the news user) runs on `_make_news_sentinel_model`'s fail-closed sentinel
    backend. A parrot replay must never invoke an LLM; making that a runtime tripwire (any inference
    entry point raises) is stronger than asserting it in a comment.
  - The Bernoulli news schedule is NOT drawn. News is carried by the schedule's own `news_post`
    slots, which came from the registered window's measured news events; drawing the harness's
    schedule as well would inject exogenous immigrants the matched null never registered.

`graph_sha256` (canonical JSON of the edge list IN DRAWN ORDER) rides in the payload as the
paired-graph provenance the Task-7 orchestrator verifies across each width triple: `build_follow_edges`
is a pure function of the schedule seed, so the three widths of one schedule MUST agree on it, and a
disagreement means the pairing was broken by something other than the knob.

CROSS-DATABASE ID COMPARISON IS INVALID (rev-2 blocker 5). Each violator post is inserted into the
run's own database, shifting every subsequent post id relative to the baseline run. Identifying the
violator's additions by differencing two runs' id sets would therefore mis-identify them. The
violator's own returned ids are recorded explicitly in `violator_item_ids`, in ledger order, and that
record is the ONLY sanctioned identification.

THE REFRESH LEDGER (rev-2 blocker 4) is keyed by the IMMUTABLE schedule-action index — the position
of the refresh in `envelope.actions` — never by a running counter over the refreshes that happened,
because a tolerated empty refresh writes no trace row (pinned by
`tests/test_parrot_v2_substrate.py::test_empty_refresh_returns_no_posts_and_writes_no_trace`) and a
counter would silently re-key every later entry. Served entries are then cross-checked 1:1 IN ORDER
against the strict loader's `RefreshRecord`s: same count, same served sets. A mismatch is a fail-stop
here, in the replayer, rather than a discrepancy discovered downstream.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import random
import subprocess
import sys
import time

import critaudit.sim.controls.parrot_v2_spec as parrot_v2_spec
from critaudit.sim.controls.parrot_v2_records import (
    emission_record_bytes,
    served_hash,
)
from critaudit.sim.controls.parrot_v2_schedule import (
    ScheduleEnvelope,
    envelope_from_bytes,
    envelope_to_bytes,
)
from critaudit.sim.harness import harness_spec as hs
from critaudit.sim.harness import oasis_adapter
from critaudit.sim.harness.assemble import assemble_harness_run
from critaudit.sim.harness.oasis_adapter import build_follow_edges, load_harness_records
from critaudit.sim.harness.observables import compute_observables

__all__ = [
    "REPLAY_PAYLOAD_KEYS",
    "replay_envelope",
    "write_replay_output",
    "read_replay_output",
    "run_replay_subprocess",
    "main",
]

# The payload's key set, pinned: Task 6 (invariance comparison) and Task 7 (orchestration) both read
# it, so a key added or dropped must break loudly here rather than downstream.
REPLAY_PAYLOAD_KEYS = (
    "schema", "schedule_seed", "assigned_window", "profile_sha256", "platform_seed",
    "schedule_sha256", "graph_sha256", "width", "n_rounds", "violator", "emission_record_b64",
    "observables", "refresh_ledger", "violator_item_ids", "timings")

# Sentinel endpoint identity for the fail-closed backend. Construction-time only: every inference
# entry point of `_make_news_sentinel_model`'s backend raises, so these values can never be dialled.
_SENTINEL_MODEL_ID = hs.MODEL_ID
_SENTINEL_ENDPOINT = "http://127.0.0.1:1/v1"     # unroutable by construction
_SENTINEL_TOKEN = "parrot-v2-replay-sentinel"    # never sent; the backend cannot reach a client

_TIMESTAMP_COL = "created_at"      # the Task-1 confirmed time column


# --- envelope validation ----------------------------------------------------------------------

def _validate_envelope(envelope):
    """Validate the envelope BEFORE anything is constructed: exact type, current schema, RECOMPUTED
    `schedule_sha256`, and the `platform_seed` the spec derives from the schedule seed.

    The digest recomputation is delegated to the Task-4 codec round trip
    (`envelope_from_bytes(envelope_to_bytes(...))`), which is itself fail-closed on schema, on
    byte-canonicality and on a stale-but-canonical digest — so there is exactly ONE implementation
    of "is this envelope self-consistent", and this module cannot drift from it."""
    if type(envelope) is not ScheduleEnvelope:
        raise TypeError("envelope must be exactly ScheduleEnvelope")
    if envelope.schema != parrot_v2_spec.SCHEMA:
        raise ValueError(
            f"replay_envelope: envelope schema {envelope.schema!r} is not the spec's "
            f"{parrot_v2_spec.SCHEMA} (fail-closed)")
    envelope_from_bytes(envelope_to_bytes(envelope))       # recomputes + rejects a stale digest
    expected_seed = parrot_v2_spec.platform_seed(envelope.schedule_seed)
    if int(envelope.platform_seed) != expected_seed:
        raise ValueError(
            f"replay_envelope: envelope platform_seed {envelope.platform_seed!r} is not the spec's "
            f"platform_seed({envelope.schedule_seed}) = {expected_seed} (fail-closed)")


def _n_rounds(envelope):
    """Round count = max scheduled round + 1. The envelope carries no explicit count (a schedule is
    defined by its actions), so it is derived; an empty schedule is a fail-stop rather than a
    zero-round no-op."""
    if not envelope.actions:
        raise ValueError("replay_envelope: envelope has no actions (fail-closed)")
    return max(int(a.round) for a in envelope.actions) + 1


# --- construction (mirrors oasis_adapter._run_oasis_minimal_async's construction block) ---------

def _build_platform_and_graph(*, width, database_path):
    """The cohort driver's construction block, mirrored. Returns (graph, platform, env)."""
    from oasis import ActionType, AgentGraph, Platform, SocialAgent, make
    from oasis.social_platform.channel import Channel
    from oasis.social_platform.typing import RecsysType

    n_agents = int(hs.OPERATING_POINT["n_agents"])
    available = [ActionType(name) for name in oasis_adapter._MINIMAL_ACTION_NAMES]

    # ONE fail-closed sentinel backend, shared by the whole graph: a parrot replay is scripted, so
    # ANY LLM invocation is a bug and must raise rather than silently emit (the cohort driver gives
    # this backend to the news user alone; here it covers the crowd too).
    sentinel = oasis_adapter._make_news_sentinel_model(
        model_id=_SENTINEL_MODEL_ID, endpoint_url=_SENTINEL_ENDPOINT, token=_SENTINEL_TOKEN,
        max_tokens=hs.COHORT_MAX_TOKENS, temperature=oasis_adapter.TEMPERATURE,
        timeout=oasis_adapter.CLIENT_TIMEOUT_S, context_budget=hs.COHORT_CONTEXT_BUDGET)

    graph = AgentGraph()
    for i in range(n_agents):
        graph.add_agent(SocialAgent(
            agent_id=i,
            user_info=oasis_adapter._new_user_info(
                name=f"user_{i}", bio=oasis_adapter._CROWD_BIO,
                user_profile=oasis_adapter._CROWD_USER_PROFILE),
            model=sentinel, available_actions=available))
    news_id = hs.NEWS_USER_AGENT_ID                      # = n_agents (harness_spec's own rule)
    graph.add_agent(SocialAgent(
        agent_id=news_id,
        user_info=oasis_adapter._new_user_info(
            name=oasis_adapter.NEWS_AGENT_NAME, bio=oasis_adapter._NEWS_BIO,
            user_profile=oasis_adapter._NEWS_USER_PROFILE),
        model=sentinel, available_actions=available))

    platform = Platform(
        db_path=database_path,
        channel=Channel(),
        recsys_type=RecsysType(hs.RECSYS_TYPE),
        refresh_rec_post_count=int(width),               # THE knob under test
        max_rec_post_len=parrot_v2_spec.MAX_REC_POST_LEN,
        following_post_count=hs.FOLLOWING_POST_COUNT,
    )
    env = make(agent_graph=graph, platform=platform, database_path=database_path)
    return graph, platform, env


def _graph_sha256(edges) -> str:
    return hashlib.sha256(
        json.dumps([list(e) for e in edges], separators=(",", ":")).encode()).hexdigest()


async def _realize_follows(graph, edges):
    """The cohort driver's realization block, verbatim in behaviour: sequential awaited
    SocialAction.follow in DRAWN order, each mirrored into the in-memory graph; fail-closed on a
    failed insert (no silent partial graph)."""
    for (u, v) in edges:
        result = await graph.get_agent(u).env.action.follow(v)
        if not (isinstance(result, dict) and result.get("success")):
            raise ValueError(f"follow realization failed for edge ({u} -> {v}): {result!r}")
        graph.add_edge(u, v)


# --- action dispatch --------------------------------------------------------------------------

def _post_db_id(item_id, *, what):
    """The integer post id behind a captured `post:<id>` item id. Comments are captured but are
    never targets, so a `comment:<id>` here is a schedule/protocol bug, not a tolerated case."""
    if not isinstance(item_id, str) or not item_id.startswith("post:"):
        raise ValueError(f"{what}: target {item_id!r} is not a post: item id (fail-closed)")
    return int(item_id.split(":", 1)[1])


def _returned_id(result, key, *, what):
    """The id an emit returned, fail-closed: a non-dict, an unsuccessful action, or a missing id key
    is a fail-stop. A scripted action that the platform refused means the schedule and the platform
    disagree — exactly the condition the replay must never paper over."""
    if not isinstance(result, dict) or result.get("success") is not True:
        raise ValueError(f"{what}: action failed (fail-closed): {result!r}")
    if key not in result:
        raise ValueError(f"{what}: action return lacks {key!r} (fail-closed): {result!r}")
    return int(result[key])


async def _dispatch_emission(action, agent_action, action_id_map, *, what):
    """Perform one scheduled EMISSION through the two-arg agent action path and record the id it
    created in `action_id_map[emission_index]`."""
    kind = action.kind
    if kind in ("create_post", "news_post"):
        result = await agent_action.create_post(action.content)
        item_id = f"post:{_returned_id(result, 'post_id', what=what)}"
    elif kind == "create_comment":
        target = _post_db_id(action_id_map[action.target_ref], what=what)
        result = await agent_action.create_comment(target, action.content)
        item_id = f"comment:{_returned_id(result, 'comment_id', what=what)}"
    elif kind == "quote_post":
        target = _post_db_id(action_id_map[action.target_ref], what=what)
        result = await agent_action.quote_post(target, action.content)
        item_id = f"post:{_returned_id(result, 'post_id', what=what)}"
    elif kind == "repost":
        target = _post_db_id(action_id_map[action.target_ref], what=what)
        result = await agent_action.repost(target)
        item_id = f"post:{_returned_id(result, 'post_id', what=what)}"
    else:
        raise ValueError(f"{what}: unknown scheduled action kind {kind!r} (fail-closed)")
    if action.emission_index is None:
        raise ValueError(f"{what}: emission action carries no emission_index (fail-closed)")
    if action.emission_index in action_id_map:
        raise ValueError(f"{what}: duplicate emission_index {action.emission_index} (fail-closed)")
    action_id_map[action.emission_index] = item_id


async def _dispatch_refresh(agent_action, *, what):
    """Perform one scheduled REFRESH. Returns (outcome, served_item_ids).

    EXACTLY ONE unsuccessful return is tolerated, and only on its exact message: an empty rec table
    with no follow-feed posts (`parrot_v2_spec.REFRESH_EMPTY_OK`, pinned by the substrate test).
    Every other failure is a fail-stop — a refresh that errored is not an empty refresh."""
    result = await agent_action.refresh()
    if not isinstance(result, dict):
        raise ValueError(f"{what}: refresh returned {result!r} (fail-closed)")
    if result.get("success") is True:
        posts = result.get("posts")
        if posts is None:
            raise ValueError(f"{what}: successful refresh lacks 'posts' (fail-closed): {result!r}")
        return "served", [f"post:{p['post_id']}" for p in posts]
    if result.get("message") == parrot_v2_spec.REFRESH_EMPTY_OK:
        return "empty", []
    raise ValueError(f"{what}: refresh failed (fail-closed): {result!r}")


# --- the replay -------------------------------------------------------------------------------

async def replay_envelope(envelope, *, width, database_path, violator=False) -> dict:
    """Drive the installed OASIS platform through ONE schedule at ONE width, serially, and return
    the replay payload. See the module docstring for the frozen protocol; every step below is that
    protocol, in order."""
    t_start = time.perf_counter()
    _validate_envelope(envelope)
    width = int(width)
    violator = bool(violator)
    n_rounds = _n_rounds(envelope)

    graph, platform, env = _build_platform_and_graph(width=width, database_path=database_path)
    await env.reset()

    edges = build_follow_edges(
        envelope.schedule_seed,
        n_agents=hs.OPERATING_POINT["n_agents"],
        density=hs.OPERATING_POINT["network_density"])
    graph_sha = _graph_sha256(edges)

    by_round = {}
    for schedule_index, action in enumerate(envelope.actions):
        by_round.setdefault(int(action.round), []).append((schedule_index, action))

    action_id_map = {}          # emission_index -> created item id ('post:N' / 'comment:N')
    refresh_ledger = []         # one entry per SCHEDULED refresh, in schedule order
    violator_item_ids = []      # the violator's extra posts, in ledger order

    t_construct = time.perf_counter()
    try:
        await _realize_follows(graph, edges)
        t_follows = time.perf_counter()

        for r in range(n_rounds):
            if platform.sandbox_clock.time_step != r:
                raise ValueError(
                    f"replay_envelope: clock is {platform.sandbox_clock.time_step} at the start of "
                    f"round {r} (fail-closed)")
            await platform.update_rec_table()

            for schedule_index, action in by_round.get(r, ()):
                what = (f"replay_envelope: round {r} schedule action {schedule_index} "
                        f"({action.kind}, agent {action.agent_id})")
                agent_action = graph.get_agent(int(action.agent_id)).env.action
                if action.kind == "refresh":
                    outcome, served = await _dispatch_refresh(agent_action, what=what)
                    refresh_ledger.append({
                        "schedule_index": schedule_index,
                        "agent_id": int(action.agent_id),
                        "round": r,
                        "outcome": outcome,
                        "served_item_ids": sorted(served),
                        "trace_seq": None,
                    })
                    if violator:
                        # The signed violator contract: EVERY scheduled refresh (served OR the
                        # tolerated empty one) is followed immediately by the same agent posting
                        # the served set's hash. No emission_index, never a target.
                        result = await agent_action.create_post(served_hash(served))
                        violator_item_ids.append(
                            f"post:{_returned_id(result, 'post_id', what=what + ' [violator]')}")
                else:
                    await _dispatch_emission(action, agent_action, action_id_map, what=what)

            platform.sandbox_clock.time_step += 1
            if platform.sandbox_clock.time_step != r + 1:
                raise ValueError(
                    f"replay_envelope: clock is {platform.sandbox_clock.time_step} after ticking "
                    f"round {r} (fail-closed)")

        platform.db.commit()
    finally:
        await env.close()
    t_rounds = time.perf_counter()

    events, refreshes, _ = load_harness_records(database_path, timestamp_col=_TIMESTAMP_COL)
    run = assemble_harness_run(events, refreshes)
    observables = compute_observables(run)
    _crosscheck_refresh_ledger(refresh_ledger, refreshes)
    t_export = time.perf_counter()

    payload = {
        "schema": parrot_v2_spec.SCHEMA,
        "schedule_seed": int(envelope.schedule_seed),
        "assigned_window": int(envelope.assigned_window),
        "profile_sha256": envelope.profile_sha256,
        "platform_seed": int(envelope.platform_seed),
        "schedule_sha256": envelope.schedule_sha256,
        "graph_sha256": graph_sha,
        "width": width,
        "n_rounds": n_rounds,
        "violator": violator,
        "emission_record_b64": base64.b64encode(emission_record_bytes(events)).decode("ascii"),
        "observables": observables,
        "refresh_ledger": refresh_ledger,
        "violator_item_ids": violator_item_ids,
        "timings": {
            "construct_s": t_construct - t_start,
            "follows_s": t_follows - t_construct,
            "rounds_s": t_rounds - t_follows,
            "export_s": t_export - t_rounds,
            "total_s": t_export - t_start,
        },
    }
    if tuple(payload) != REPLAY_PAYLOAD_KEYS:
        raise ValueError("replay_envelope: payload key set drifted from REPLAY_PAYLOAD_KEYS")
    return payload


def _crosscheck_refresh_ledger(refresh_ledger, refreshes):
    """Cross-check the SERVED ledger entries 1:1, IN ORDER, against the strict loader's
    RefreshRecords — same count, same served sets — and take each entry's `trace_seq` from its
    matched record. The replay is serial, so the trace's rowid order IS the schedule order; a
    divergence means the ledger and the database disagree about what was read, which invalidates
    every downstream exposure claim and is therefore a fail-stop here."""
    served_entries = [e for e in refresh_ledger if e["outcome"] == "served"]
    if len(served_entries) != len(refreshes):
        raise ValueError(
            f"replay_envelope: {len(served_entries)} served refresh ledger entries but "
            f"{len(refreshes)} traced RefreshRecords (fail-closed)")
    for entry, record in zip(served_entries, refreshes):
        if set(entry["served_item_ids"]) != set(record.served_item_ids):
            raise ValueError(
                f"replay_envelope: ledger entry {entry['schedule_index']} served "
                f"{entry['served_item_ids']!r} but the traced RefreshRecord served "
                f"{sorted(record.served_item_ids)!r} (fail-closed)")
        entry["trace_seq"] = int(record.seq)


# --- output codec (atomic write + digest sidecar; the REAL codec Task 7's fakes also use) -------

def _payload_bytes(payload) -> bytes:
    return (
        json.dumps(payload, allow_nan=False, ensure_ascii=False, separators=(",", ":"),
                   sort_keys=True)
        + "\n"
    ).encode("utf-8")


def sidecar_path(out_path) -> str:
    return f"{out_path}.sha256"


def write_replay_output(payload, out_path):
    """Write the payload ATOMICALLY (`.tmp` + `os.replace`) with a `.sha256` sidecar.

    Atomicity matters because a replay output is read by a DIFFERENT process (the Task-7
    orchestrator) that may look while the child is writing: `os.replace` makes the file appear whole
    or not at all. The payload lands before the sidecar, so a crash between the two leaves an output
    with no digest — which `read_replay_output` refuses, rather than an output with a digest that
    does not describe it."""
    data = _payload_bytes(payload)
    directory = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(directory, exist_ok=True)
    tmp = f"{out_path}.tmp"
    with open(tmp, "wb") as handle:
        handle.write(data)
    os.replace(tmp, out_path)
    digest = hashlib.sha256(data).hexdigest()
    sha_path = sidecar_path(out_path)
    sha_tmp = f"{sha_path}.tmp"
    with open(sha_tmp, "w") as handle:
        handle.write(digest + "\n")
    os.replace(sha_tmp, sha_path)
    return out_path, sha_path


def read_replay_output(out_path):
    """Read a replay payload, VERIFYING THE SIDECAR DIGEST BEFORE DECODING. A truncated, appended-to
    or otherwise altered output is rejected as bytes; nothing downstream ever sees a parsed value
    that the digest did not cover."""
    sha_path = sidecar_path(out_path)
    if not os.path.exists(sha_path):
        raise ValueError(f"replay output {out_path!r} has no digest sidecar (fail-closed)")
    with open(sha_path, "r") as handle:
        expected = handle.read().strip()
    with open(out_path, "rb") as handle:
        data = handle.read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise ValueError(
            f"replay output {out_path!r} digest {actual} does not match the sidecar digest "
            f"{expected} (fail-closed)")
    try:
        return json.loads(data)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError(f"replay output {out_path!r} is not valid JSON: {exc}")


# --- subprocess boundary ------------------------------------------------------------------------

def run_replay_subprocess(envelope_path, *, width, database_path, out_path, violator, timeout):
    """Run ONE replay in a FRESH interpreter.

    The subprocess boundary is load-bearing, not hygiene: the child seeds the GLOBAL `random` module
    with the envelope's platform seed (OASIS's recommender samples on it, platform.py:277 /
    recsys.py), and a global module seeded inside a long-lived parent would carry state across
    replays. A fresh process makes each replay's platform sampling a pure function of its seed."""
    cmd = [sys.executable, "-m", "critaudit.experiments.parrot_v2_replay",
           "--envelope", str(envelope_path),
           "--width", str(int(width)),
           "--db", str(database_path),
           "--out", str(out_path)]
    if violator:
        cmd.append("--violator")
    child_env = dict(os.environ)
    child_env["PYTHONPATH"] = "src"
    return subprocess.run(cmd, env=child_env, check=True, timeout=timeout,
                          capture_output=True, text=True)


def main(argv=None):
    """The child entry point (module level so macOS's spawn start method can import it).

    ORDER IS THE CONTRACT: the envelope is loaded (fail-closed on its own digest), then
    `random.seed(platform_seed)` runs BEFORE any OASIS object exists, then the replay, then the
    atomic write. Any exception propagates and the process exits non-zero — a partial or unwritten
    output is always preferable to one produced under an unseeded recommender."""
    parser = argparse.ArgumentParser(
        description="Replay ONE parrot-v2 schedule envelope at ONE recommender width.")
    parser.add_argument("--envelope", required=True, help="path to canonical envelope bytes")
    parser.add_argument("--width", required=True, type=int, help="refresh_rec_post_count")
    parser.add_argument("--db", required=True, help="path for the replay's OASIS sqlite database")
    parser.add_argument("--out", required=True, help="path for the replay output payload")
    parser.add_argument("--violator", action="store_true", help="run the violator arm")
    args = parser.parse_args(argv)

    with open(args.envelope, "rb") as handle:
        envelope = envelope_from_bytes(handle.read())
    random.seed(envelope.platform_seed)          # FIRST: the platform samples on global random
    payload = asyncio.run(replay_envelope(
        envelope, width=args.width, database_path=args.db, violator=args.violator))
    write_replay_output(payload, args.out)
    return 0


if __name__ == "__main__":
    main()
