# tests/test_harness_positive_control.py
import os

import numpy as np
import pytest
from critaudit.sim.harness.types import HarnessRun
from critaudit.sim.harness.positive_control import check_positive_control

def _coupled_run():
    # one tree of 4 (root + 3 read->emit replies) -> not all size-1, not one giant, read_emit>0
    times = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    parent_idx = np.array([-1, 0, 1, -1, 3, 0], dtype=np.int64)
    root_id = np.array([0, 0, 0, 3, 3, 0], dtype=np.int64)
    read_emit = np.array([False, True, True, False, True, True])
    content = ["aaaa", "bbbbbbbb", "cc", "dddddddddd", "e", "ffffff"]
    return HarnessRun(times, root_id, parent_idx, read_emit, content)

def _degenerate_all_size1():
    n = 6
    times = np.arange(n, dtype=float)
    parent_idx = np.full(n, -1, dtype=np.int64)
    root_id = np.arange(n, dtype=np.int64)
    read_emit = np.zeros(n, dtype=bool)
    content = ["x"] * n
    return HarnessRun(times, root_id, parent_idx, read_emit, content)

def _giant_only():
    # ONE tree swallowing ALL events (a degenerate single-component crowd) -> trips ONLY the giant check.
    # Hand-computed: sizes=[6], n_events=6 -> frac_size1 = 0/1 = 0.0 (clears <=0.95, single multi-event
    # tree has no size-1 trees); read_emit ratio = 4/6 ~= 0.667 (clears >0.01); length_spread =
    # std([4,8,2,10,1,6]) ~= 3.18 (clears >1.0); giant_frac = 6/6 = 1.0 > 0.90 is the SOLE failing check.
    times = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    parent_idx = np.array([-1, 0, 1, 0, 3, 0], dtype=np.int64)
    root_id = np.array([0, 0, 0, 0, 0, 0], dtype=np.int64)
    read_emit = np.array([False, True, True, False, True, True])
    content = ["aaaa", "bbbbbbbb", "cc", "dddddddddd", "e", "ffffff"]
    return HarnessRun(times, root_id, parent_idx, read_emit, content)

def _empty_run():
    # A degraded/timeout reference trace with ZERO events (empty arrays, empty content list).
    return HarnessRun(np.array([]), np.array([], dtype=np.int64),
                      np.array([], dtype=np.int64), np.array([], dtype=bool), [])

def test_positive_control_passes_on_coupled():
    diag = check_positive_control(_coupled_run())
    assert diag["read_emit_ratio"] > 0.0

def test_positive_control_raises_on_degenerate():
    # expected AssertionError on a degenerate (all size-1, no read->emit) crowd.
    # pytest.raises replaces the original try/except-AssertionError idiom, whose `assert False`
    # sentinel was ITSELF caught by the except (the expected exception IS AssertionError) — a
    # zero-power test that passed whether or not the gate raised (found via the gate-integrity
    # power-check discipline; the sibling ValueError-expecting tests elsewhere are unaffected,
    # their sentinel propagates).
    with pytest.raises(AssertionError):
        check_positive_control(_degenerate_all_size1())

def test_positive_control_raises_on_giant_only():
    # Regression guard on the giant_frac failure path — the ONE threshold no other fixture trips
    # (and simultaneously the tightest coupled-fixture margin). The fixture isolates giant_frac: only
    # that check fails (see _giant_only hand-computation), so a silent-always-pass drift in
    # harness_spec.MAX_GIANT_FRAC (e.g. a bound mis-set > 1.0) would surface HERE and nowhere else.
    # pytest.raises (not try/except + `assert False`) is deliberate: the latter idiom would SWALLOW the
    # very AssertionError under test, giving a false green when the gate stops enforcing (teeth check).
    with pytest.raises(AssertionError):
        check_positive_control(_giant_only())

def test_positive_control_raises_labelled_on_empty():
    # An empty/degraded reference must fail the gate LOUDLY with a LABELLED AssertionError — the guard
    # exists precisely so this is NOT an incidental ZeroDivisionError from the frac_size1 division (0/0).
    # Live scenario: this sub-increment already produced a timeout-degraded OASIS trace (design §8/§9).
    with pytest.raises(AssertionError):
        check_positive_control(_empty_run())


# --- @slow GPU cohort: the reference operating point through the self-hosted endpoint (design §8/§10;
#     plan Task 10 Step 3). Env-gated skip on HARNESS_ENDPOINT_URL; run deliberately, once, with the
#     Modal endpoint up (see task9-rehearsal-report.md). Interpreter: ~/oasis_venv/bin/python. -----

@pytest.mark.slow
def test_reference_cohort_positive_control():
    url = os.environ.get("HARNESS_ENDPOINT_URL")
    token = os.environ.get("HARNESS_ENDPOINT_TOKEN")
    if not url:
        pytest.skip("no Modal endpoint configured (set HARNESS_ENDPOINT_URL)")
    from critaudit.experiments.llm_harness import run_reference_cohort
    results = run_reference_cohort(url, token, timestamp_col="created_at")
    assert len(results) == 3
    for r in results:
        assert r["read_emit_ratio"] > 0.0   # accessibility + coupling present (NOT a regime claim)


# --- @slow construction-half integration ($0, NO LLM, NO endpoint): verify the FROZEN network + news
#     construction machinery runs end-to-end against installed camel-oasis 0.2.5. @slow because it
#     imports the heavy OASIS stack (keeping the fast suite OASIS-free), but it needs no GPU/endpoint
#     and runs without HARNESS_ENDPOINT_URL. -----------------------------------------------------

@pytest.mark.slow
def test_construction_half_no_llm(tmp_path):
    # Builds 6 crowd + 1 manual news user, realizes the frozen follow graph, runs news-ONLY rounds
    # (no LLMAction -> crowd never acts), then asserts the DB. Crowd uses a keyless NEVER-CALLED
    # backend: model=None is NOT usable here (ChatAgent resolves None -> ModelFactory.create(DEFAULT
    # gpt-4.1-mini) -> raises without OPENAI_API_KEY) — the measured freeze-vs-reality fact. The news
    # user gets the FAIL-CLOSED SENTINEL (as in run_oasis_minimal; controller ratification
    # 2026-07-14): this test PASSING is the proof the tripwire has the right scope — the news user's
    # ManualAction(CREATE_POST) dispatch must NOT trip it (inference dispatch is fatal, tested apart).
    import asyncio
    import sqlite3

    from camel.models import ModelFactory
    from camel.types import ModelPlatformType
    from oasis import (ActionType, AgentGraph, LLMAction, ManualAction, Platform,  # noqa: F401
                       SocialAgent, make)
    from oasis.social_platform.channel import Channel
    from oasis.social_platform.typing import RecsysType

    from critaudit.sim.harness import harness_spec as hs
    from critaudit.sim.harness.oasis_adapter import (
        MAX_REC_POST_LEN, _MINIMAL_ACTION_NAMES, _make_news_sentinel_model, _new_user_info,
        build_follow_edges, build_news_schedule, export_harness_run)

    n_agents, density, n_rounds, news_rate, seed = 6, 0.10, 6, 0.5, 20260627
    db = str(tmp_path / "construction.db")
    edges = build_follow_edges(seed, n_agents=n_agents, density=density)
    schedule = build_news_schedule(seed, n_rounds=n_rounds, news_rate=news_rate)
    expected_news = [c for c in schedule if c is not None]
    assert len(edges) == 3 and len(expected_news) >= 1   # chosen fixture: M(6)=3, a non-trivial mix

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
        model_type="construction-never-called", url="http://127.0.0.1:1/v1", api_key="unused",
        model_config_dict={"temperature": 0.7, "max_tokens": 4096}, timeout=5)
    news_model = _make_news_sentinel_model(
        model_id="construction-never-called", endpoint_url="http://127.0.0.1:1/v1", token="unused",
        max_tokens=4096, temperature=0.7, timeout=5)
    available = [ActionType(name) for name in _MINIMAL_ACTION_NAMES]

    async def build_and_run():
        graph = AgentGraph()
        for i in range(n_agents):
            graph.add_agent(SocialAgent(
                agent_id=i, user_info=_new_user_info(name=f"user_{i}", bio="b", user_profile="p"),
                model=model, available_actions=available))
        news_id = n_agents
        graph.add_agent(SocialAgent(
            agent_id=news_id, user_info=_new_user_info(name="news", bio="b", user_profile="p"),
            model=news_model, available_actions=available))   # SENTINEL: manual-only, enforced
        platform = Platform(
            db_path=db, channel=Channel(), recsys_type=RecsysType(hs.RECSYS_TYPE),
            refresh_rec_post_count=hs.OPERATING_POINT["social_influence"],
            max_rec_post_len=MAX_REC_POST_LEN)
        env = make(agent_graph=graph, platform=platform, database_path=db)
        await env.reset()
        for (u, v) in edges:
            res = await graph.get_agent(u).env.action.follow(v)
            assert isinstance(res, dict) and res.get("success"), res
            graph.add_edge(u, v)
        news_agent = graph.get_agent(news_id)
        for r in range(n_rounds):
            actions = {}
            if schedule[r] is not None:
                actions[news_agent] = ManualAction(
                    action_type=ActionType.CREATE_POST, action_args={"content": schedule[r]})
            await env.step(actions)   # NO LLMAction anywhere -> zero LLM traffic by construction
        await env.close()

    asyncio.run(build_and_run())

    con = sqlite3.connect(db)
    try:
        n_follow = con.execute("SELECT COUNT(*) FROM follow").fetchone()[0]
        news_posts = [c for (c,) in con.execute(
            "SELECT content FROM post WHERE user_id=? ORDER BY post_id", (n_agents,))]
        crowd_emits = con.execute(
            "SELECT COUNT(*) FROM trace WHERE action IN "
            "('create_post','create_comment','repost','quote_post') AND user_id != ?",
            (n_agents,)).fetchone()[0]
        n_refresh = con.execute("SELECT COUNT(*) FROM trace WHERE action='refresh'").fetchone()[0]
    finally:
        con.close()

    assert n_follow == len(edges) == 3        # DB follow table = the realized graph, exact M(6)
    assert news_posts == expected_news        # news posts present, matching the drawn schedule
    assert crowd_emits == 0                    # zero LLM traffic (crowd never LLM-driven)
    assert n_refresh == 0                      # crowd never refreshed; the news user never refreshes
    # the exported stream is exactly the news roots (the exogenous immigrants the axis supplies)
    run = export_harness_run(db, timestamp_col="created_at")
    assert int(run.times.size) == len(expected_news)


# --- @slow (imports CAMEL; $0, NO network): the driver-side token accountant SUMS usage across every
#     model call. Verifies the accumulation contract directly (a real completion carries the same
#     .usage fields CAMEL reads, chat_agent.py:2542-2544) without hitting an endpoint. --------------

@pytest.mark.slow
def test_usage_accounting_sums_across_calls():
    from critaudit.sim.harness.oasis_adapter import _make_counting_model

    class _FakeUsage:
        def __init__(self, p, c, t):
            self.prompt_tokens, self.completion_tokens, self.total_tokens = p, c, t

    class _FakeResult:
        def __init__(self, usage):
            self.usage = usage

    m = _make_counting_model(model_id="never-called", endpoint_url="http://127.0.0.1:1/v1",
                             token="unused", max_tokens=64, temperature=0.7, timeout=5)
    assert m.usage_counts == {"prompt": 0, "completion": 0, "total": 0, "n_calls": 0}
    m._accumulate(_FakeResult(_FakeUsage(10, 3, 13)))
    m._accumulate(_FakeResult(_FakeUsage(20, 5, 25)))
    m._accumulate(_FakeResult(None))          # a usage-less result counts the call, adds no tokens
    assert m.usage_counts == {"prompt": 30, "completion": 8, "total": 38, "n_calls": 3}


# --- @slow (imports CAMEL+OASIS; $0, NO network): the news user's FAIL-CLOSED SENTINEL model
#     (controller ratification 2026-07-14): "model-free by frozen NEWS_AUTHOR_RULE" is ENFORCED at
#     runtime, not assumed — any inference call on the news backend is a driver bug and must raise.
#     Scope check is two-sided: construction + manual dispatch clean (the ManualAction path in
#     test_construction_half_no_llm, which wires this sentinel); inference dispatch fatal (here). ---

@pytest.mark.slow
def test_news_sentinel_constructs_but_blocks_all_inference():
    import asyncio

    from oasis.social_platform.typing import ActionType

    from critaudit.sim.harness.oasis_adapter import (
        _MINIMAL_ACTION_NAMES, _make_news_sentinel_model, _new_user_info)

    sentinel = _make_news_sentinel_model(
        model_id="never-called", endpoint_url="http://127.0.0.1:1/v1", token="unused",
        max_tokens=64, temperature=0.7, timeout=5)

    # constructs cleanly INSIDE a SocialAgent (subclasses ChatAgent): every construction-time touch
    # (ModelManager wrap, token_counter, token_limit -> memory context creator) works.
    from oasis import SocialAgent
    agent = SocialAgent(
        agent_id=7, user_info=_new_user_info(name="news", bio="b", user_profile="p"),
        model=sentinel, available_actions=[ActionType(n) for n in _MINIMAL_ACTION_NAMES])
    assert agent.social_agent_id == 7

    msgs = [{"role": "user", "content": "hi"}]
    # the inner entry points every inference path funnels through (base_model.py run->_run,
    # arun->_arun; ChatAgent/ModelManager call only run/arun)
    with pytest.raises(AssertionError, match="model-free"):
        sentinel._run(msgs)
    with pytest.raises(AssertionError, match="model-free"):
        asyncio.run(sentinel._arun(msgs))
    # the PUBLIC funnel (metaclass-wrapped run -> preprocess -> _run) raises too
    with pytest.raises(AssertionError, match="model-free"):
        sentinel.run(msgs)
    # belt-and-braces: the direct client helpers cannot escape either
    with pytest.raises(AssertionError, match="model-free"):
        sentinel._request_chat_completion(msgs)
    with pytest.raises(AssertionError, match="model-free"):
        asyncio.run(sentinel._arequest_chat_completion(msgs))
