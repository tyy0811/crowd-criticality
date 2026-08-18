# tests/test_parrot_v2_schedule.py
import dataclasses, pytest
from critaudit.sim.controls.parrot_v2_profile import CohortActionProfile
from critaudit.sim.controls.parrot_v2_schedule import (
    ScheduleAction, build_schedule_envelope, envelope_from_bytes,
    envelope_sha256, envelope_to_bytes, repost_target_valid, stored_original)
from critaudit.sim.controls.parrot_v2_profile import profile_sha256
import critaudit.sim.controls.parrot_v2_spec as spec


def _profile(window_seed=20260627, **over):
    base = dict(
        window_seed=window_seed,
        per_round_type_counts=((2, 0, 0, 0), (0, 1, 1, 1)),   # news-ADJUSTED
        per_round_refresh_counts=(1, 2),
        news_events=((1, "NEWS ITEM"),),
        authored_corpus=("alpha", "beta", "gamma"),
    )
    base.update(over)
    return CohortActionProfile(**base)


def test_envelope_identity_and_codec():
    env = build_schedule_envelope(_profile(), 818201)     # window 20260627 (round-robin)
    assert env.schema == spec.SCHEMA
    assert env.schedule_seed == 818201
    assert env.assigned_window == 20260627
    assert env.profile_sha256 == profile_sha256(_profile())
    assert env.platform_seed == spec.platform_seed(818201)
    data = envelope_to_bytes(env)
    assert envelope_from_bytes(data) == env
    assert len(envelope_sha256(env)) == 64
    with pytest.raises(ValueError):
        envelope_from_bytes(data + b" ")
    tampered = dataclasses.replace(env, schedule_sha256="0" * 64)
    with pytest.raises(ValueError, match="schedule_sha256"):
        envelope_from_bytes(envelope_to_bytes(tampered))
    with pytest.raises(ValueError, match="window"):
        build_schedule_envelope(_profile(window_seed=20260628), 818201)


def test_determinism():
    a = envelope_to_bytes(build_schedule_envelope(_profile(), 818201))
    b = envelope_to_bytes(build_schedule_envelope(_profile(), 818201))
    assert a == b
    c = envelope_to_bytes(build_schedule_envelope(
        _profile(window_seed=20260628), 818202))
    assert c != a


def test_accounting_order_and_content_rules():
    env = build_schedule_envelope(_profile(), 818201)
    by_round = {}
    for a in env.actions:
        by_round.setdefault(a.round, []).append(a)
    r0, r1 = by_round[0], by_round[1]
    assert [a.kind for a in r0].count("refresh") == 1
    assert [a.kind for a in r0].count("create_post") == 2
    assert [a.kind for a in r1].count("refresh") == 2
    assert [a.kind for a in r1].count("create_post") == 0
    assert [a.kind for a in r1].count("news_post") == 1
    kinds0 = [a.kind for a in r0]
    assert kinds0[:1] == ["refresh"] and set(kinds0[1:]) == {"create_post"}
    kinds1 = [a.kind for a in r1]
    assert kinds1[:2] == ["refresh", "refresh"] and kinds1[-1] == "news_post"
    for a in env.actions:
        if a.kind == "repost":
            assert a.content == ""
        elif a.kind == "news_post":
            assert a.content == "NEWS ITEM" and a.agent_id == 50
        elif a.kind == "refresh":
            assert a.content is None and a.emission_index is None
        else:
            assert a.content in ("alpha", "beta", "gamma")
    emids = [a.emission_index for a in env.actions if a.kind != "refresh"]
    assert emids == list(range(len(emids)))


def test_target_legality_and_live_predicate():
    env = build_schedule_envelope(_profile(), 818201)
    post_kinds = {"create_post", "quote_post", "repost", "news_post"}
    emissions = [a for a in env.actions if a.emission_index is not None]
    written = {}
    for a in env.actions:
        if a.kind in ("create_comment", "quote_post", "repost"):
            t = emissions[a.target_ref]
            assert t.emission_index < a.emission_index
            assert t.kind in post_kinds                    # reposts ARE valid targets
            if a.kind == "repost":
                assert repost_target_valid(emissions, written, a.agent_id, a.target_ref)
        if a.kind in ("repost", "quote_post"):
            written.setdefault(a.agent_id, set()).add(
                stored_original(emissions, a.emission_index))


def test_predicate_clauses_directly():
    """Hand-built history: both clauses fire non-vacuously (mirrors the Task-0
    written-original resolution probe)."""
    mk = lambda i, kind, agent, tref: ScheduleAction(
        round=0, kind=kind, agent_id=agent, target_ref=tref,
        content=("" if kind == "repost" else None if kind == "refresh" else "x"),
        emission_index=i)
    ems = [mk(0, "create_post", 0, None),      # e0 root
           mk(1, "quote_post", 1, 0),          # e1 = agent1 quotes e0 -> written[1]={0}
           mk(2, "repost", 2, 0),              # e2 = agent2 reposts e0 -> stored=0
           mk(3, "repost", 3, 2)]              # e3 = agent3 reposts e2 -> stored=0 (root-resolved)
    assert stored_original(ems, 0) is None
    assert stored_original(ems, 1) == 0        # quote of common -> the target itself
    assert stored_original(ems, 2) == 0        # repost of common -> the target itself
    assert stored_original(ems, 3) == 0        # repost of REPOST -> root-resolved
    written = {1: {0}, 2: {0}, 3: {0}}
    # clause 1: agent 1 (prior QUOTE of e0) may not repost e0
    assert not repost_target_valid(ems, written, 1, 0)
    # clause 2: agent 3 (prior repost rooted at e0) may not repost e2 (a repost rooted at e0)
    assert not repost_target_valid(ems, written, 3, 2)
    # clean agent may repost anything post-type
    assert repost_target_valid(ems, {}, 4, 2)


def test_empty_valid_target_set_fails_at_generation():
    bad = _profile(per_round_type_counts=((0, 1, 0, 0), (0, 0, 0, 0)),
                   per_round_refresh_counts=(0, 0), news_events=())
    with pytest.raises(ValueError, match="fail-closed at schedule generation"):
        build_schedule_envelope(bad, 818201)


def test_news_and_repost_consume_no_content_draw():
    with_news = build_schedule_envelope(_profile(), 818201)
    without = build_schedule_envelope(_profile(news_events=()), 818201)
    boot = lambda env: [a.content for a in env.actions
                        if a.kind in ("create_post", "create_comment", "quote_post")]
    assert boot(with_news) == boot(without)
