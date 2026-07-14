from __future__ import annotations
import json
import os
import sqlite3
import tempfile
import numpy as np
from critaudit.sim.harness.types import EventRecord, RefreshRecord
from critaudit.sim.harness.assemble import assemble_harness_run
from critaudit.sim.harness import harness_spec as hs


# The emit actions OASIS logs to `trace`, and the info key naming the content id each one CREATED.
# Confirmed against the OASIS source (oasis/social_platform/platform.py, recon 2026-06-30):
#   create_post    -> {"content", "post_id"}                 (post_id)
#   quote_post     -> {"quoted_id", "new_post_id"}           (new_post_id)
#   repost         -> {"reposted_id", "new_post_id"}         (new_post_id)
#   create_comment -> {"content", "comment_id"}              (comment_id)
# Each created id maps into the SAME item_id namespace used for EventRecords ('post:<id>' /
# 'comment:<id>'), so the emit's trace rowid can be joined onto its event as the `seq` tiebreaker.
_EMIT_ID_KEY = {
    "create_post": ("post", "post_id"),
    "quote_post": ("post", "new_post_id"),
    "repost": ("post", "new_post_id"),
    "create_comment": ("comment", "comment_id"),
}


def _served_post_ids(info):
    """Extract served post ids from a REFRESH trace's `info` (JSON string or already-parsed dict).
    Confirmed shape (Task 1): {"posts": [{"post_id": <id>, ...}, ...]}. FAIL-CLOSED on a shape that
    does not match (so a schema drift is a loud error, not a silent empty served set)."""
    d = json.loads(info) if isinstance(info, str) else info
    posts = d.get("posts")
    if posts is None:
        raise ValueError("REFRESH info has no 'posts' key — schema drift; re-run Task-1 recon")
    return [p["post_id"] for p in posts]


def _emit_item_id(action, info):
    """The item_id an EMIT trace row created (e.g. 'post:4' / 'comment:3'), used to join the row's
    rowid onto the matching event as its `seq`. Returns None for a non-emit action (nothing to join).
    FAIL-CLOSED: an emit action whose `info` lacks its confirmed id key is schema drift and raises
    (so a broken join surfaces loudly, never as a silent seq=0)."""
    ns_key = _EMIT_ID_KEY.get(action)
    if ns_key is None:
        return None
    ns, key = ns_key
    d = json.loads(info) if isinstance(info, str) else info
    if key not in d:
        raise ValueError(f"{action} trace info lacks {key!r} — schema drift; re-run Task-1 recon")
    return f"{ns}:{d[key]}"


def _event_seq(item_id, parent_item_id, seq_by_item):
    """The event's `seq` = the rowid of its OWN emit trace row (the counter shared with refreshes).
    STRICT join: an emit WITH a parent must have a trace row (every emit-with-parent joins cleanly on
    the real recon trace, 2026-06-30) — a missing one raises rather than defaulting seq=0, which would
    silently mis-order a same-round read->emit pair. A parentless root never enters pairing, so a
    missing trace row there is harmless (seq=0)."""
    seq = seq_by_item.get(item_id)
    if seq is not None:
        return seq
    if parent_item_id is not None:
        raise ValueError(
            f"emit {item_id!r} (parent {parent_item_id!r}) has no trace row — cannot place it in the "
            f"read->emit (created_at, rowid) ordering; un-traced emit or schema drift")
    return 0


def export_harness_run(db_path, *, timestamp_col):
    """Read the OASIS post/comment/trace tables into the normalized HarnessRun. `timestamp_col` is the
    confirmed time column ('created_at' per the Task-1 recon). The DB is opened READ-ONLY so a source
    trace (e.g. the committed recon fixture) can never be mutated.

    Two passes over the data:
      1. `trace` -> REFRESH records (seq = trace rowid) AND an item_id -> trace rowid map for every
         emit action (the seq-join source).
      2. `post`/`comment` -> EventRecords, each carrying seq from its OWN emit trace row so refresh-seq
         and emit-seq share the one counter the round-granular read->emit tiebreaker needs.
    Fail-closed throughout: `_served_post_ids`/`_emit_item_id` raise on info-shape drift, the strict
    seq-join raises on an un-traced emit-with-parent, and `assemble_harness_run`'s `build_parent_root`
    raises on an unresolvable/duplicate/out-of-order parent (surfaced, not swallowed)."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        # Pass 1: trace -> refreshes + emit(item_id) -> rowid. rowid is trace insertion order.
        refreshes = []
        seq_by_item = {}
        for rowid, uid, ts, action, info in con.execute(
                f"SELECT rowid, user_id, {timestamp_col}, action, info FROM trace ORDER BY rowid"):
            if action == "refresh":
                served = frozenset(f"post:{pid}" for pid in _served_post_ids(info))
                refreshes.append(RefreshRecord(int(uid), float(ts), served, seq=int(rowid)))
                continue
            item = _emit_item_id(action, info)
            if item is None:
                continue
            if item in seq_by_item:
                raise ValueError(f"duplicate emit trace for {item!r} (rowid {rowid}) — schema drift")
            seq_by_item[item] = int(rowid)

        # Pass 2: content rows -> events (posts before comments keeps parents before children on ties).
        events = []
        for pid, uid, orig, content, ts in con.execute(
                f"SELECT post_id, user_id, original_post_id, content, {timestamp_col} "
                f"FROM post ORDER BY post_id"):
            item_id = f"post:{pid}"
            parent = f"post:{orig}" if orig is not None else None      # NULL original_post_id = root
            events.append(EventRecord(item_id, float(ts), int(uid), parent, content or "",
                                      seq=_event_seq(item_id, parent, seq_by_item)))
        for cid, pid, uid, content, ts in con.execute(
                f"SELECT comment_id, post_id, user_id, content, {timestamp_col} "
                f"FROM comment ORDER BY comment_id"):
            item_id = f"comment:{cid}"
            parent = f"post:{pid}"                                     # a comment's parent is its post
            events.append(EventRecord(item_id, float(ts), int(uid), parent, content or "",
                                      seq=_event_seq(item_id, parent, seq_by_item)))
    finally:
        con.close()
    return assemble_harness_run(events, refreshes)


# =============================================================================================
# Task 10 — run_oasis_minimal: the OASIS-config integration realizing the FROZEN construction
# rules (harness_spec + .superpowers/sdd/phaseB-freeze-report.md §4 wiring contract). Everything
# here is faithful realization of frozen constants; no value below shadows a frozen constant.
# oasis/camel imports are LAZY (inside the functions) so importing this module for the pure
# pipeline (export_harness_run + the two builders below) never pulls the heavy OASIS stack.
# =============================================================================================

# --- Task-10 driver choices (named module constants, disclosed; NOT frozen spec constants) ----

# max_rec_post_len MUST be >= refresh_rec_post_count or refresh's sample branch never fires and the
# frozen coupling knob is silently capped (freeze report §10 / harness_spec RECSYS_TYPE wiring
# caution: Platform default max_rec_post_len=2 < frozen refresh_rec_post_count=3, platform.py:66,
# 276-278). Set to 5 = the largest value OASIS itself ships (Reddit preset refresh_rec_post_count,
# env.py:96) so the two-stage rec-buffer sample (fill buffer -> subsample refresh_rec_post_count)
# stays non-degenerate. DISCLOSED alternative: max_rec_post_len == refresh_rec_post_count exactly
# (a tighter buffer = no headroom for the subsample); 5 is a Task-10 driver choice, set result-blind
# (a buffer-capacity value, not an emitted-stream quantity), out of harness_spec's scope by its own
# statement ("exact value = Task-10 driver choice ... not a new spec constant").
MAX_REC_POST_LEN = 5

# CAMEL model_config_dict["temperature"] for the cohort. 0.7 cites the Task-1 fixture-config
# precedent (DECISIONS 2026-06-30) reused verbatim by the Task-9 $0 rehearsal + endpoint smoke
# (task9-rehearsal-report.md §2.1/§9). A sampling temperature is an input-side substrate constant
# (it does not read any emitted-stream statistic). DISCLOSED: any fixed temperature is a convention;
# 0.7 is carried forward from the recon/rehearsal for cross-run consistency, not tuned here.
TEMPERATURE = 0.7

# Client call timeout (seconds) — the Task-9 wiring fact (task9-rehearsal-report.md §3): CAMEL's
# OpenAICompatibleModel default is 180 s; the rehearsal + endpoint smoke used 600 s. Finite, generous.
CLIENT_TIMEOUT_S = 600

# Minimal action space (design §3): the four emit tools + do_nothing; REFRESH is AUTOMATIC (fired
# inside perform_action_by_llm via SocialEnvironment.to_text_prompt -> action.refresh(),
# agent_environment.py:58-59) so it is NOT listed; search/trend/group/interview EXCLUDED by omission
# (SocialAgent keeps only the tools whose name is in available_actions, agent.py:99-104). Exact enum
# names verified from the installed oasis ActionType (social_platform/typing.py:17-49). Resolved to
# ActionType members lazily inside the build (this module must not import oasis at import time).
_MINIMAL_ACTION_NAMES = ("create_post", "create_comment", "repost", "quote_post", "do_nothing")

# Neutral synthetic crowd profile (DISCLOSED convention; input-side content, NOT a persona). Every
# LLM-crowd member gets name = "user_<i>" and this one fixed neutral bio + user_profile — uniform,
# no topical/behavioural steering (contrast the Task-9 rehearsal's chatty personas, deliberately
# dropped). The bio -> DB user row (sign_up); the user_profile -> the agent system message
# ("Your have profile: <...>", config/user.py:59-63). A non-tuned convention choice.
_CROWD_BIO = "A user of an online social platform."
_CROWD_USER_PROFILE = "You are an ordinary user of an online social platform."
_NEWS_BIO = "Automated account that posts news headlines."
_NEWS_USER_PROFILE = "You are an automated news account."


def build_follow_edges(seed, *, n_agents, density):
    """PURE realization of NETWORK_GRAPH_FORM = directed exact-count G(n, M) (harness_spec:171;
    freeze report §1/A1): M = round(density*n*(n-1)) DISTINCT ordered pairs (u, v), u != v, drawn
    uniformly WITHOUT replacement over crowd ids 0..n_agents-1, on the namespaced RNG_STREAM_GRAPH
    spawn-key stream. Pair space enumerated lexicographically (index i -> u = i//(n-1);
    r = i%(n-1); v = r if r < u else r+1); sampled via rng.choice(n*(n-1), size=M, replace=False)
    -> the edge set is a pure function of `seed`. Returns list[(int u, int v)] in drawn order (the
    order run_oasis_minimal issues the sequential SocialAction.follow calls in)."""
    n = int(n_agents)
    m = round(float(density) * n * (n - 1))
    rng = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(hs.RNG_STREAM_GRAPH,)))
    idx = rng.choice(n * (n - 1), size=m, replace=False)
    edges = []
    for i in idx:
        i = int(i)
        u = i // (n - 1)
        r = i % (n - 1)
        v = r if r < u else r + 1
        edges.append((u, v))
    return edges


def build_news_schedule(seed, *, n_rounds, news_rate, pool=None):
    """PURE realization of NEWS_SCHEDULE_FORM (harness_spec:231; freeze report §2/B1-B2, B4):
    independent Bernoulli(news_rate) per round r = 1..n_rounds (ONE uniform per round, consumed in
    round order) on the RNG_STREAM_NEWS_SCHEDULE stream; on each realized injection, content is drawn
    uniformly WITH replacement from `pool` (default NEWS_POOL) on the SEPARATE RNG_STREAM_NEWS_CONTENT
    stream, consumed in injection order. Returns a length-n_rounds list; entry r is the drawn news
    string if round r injects, else None (submit-in-round-r / readable-from-r+1 is enforced by the
    driver's step timing, not encoded here). Namespaced spawn-key streams make the schedule/content
    draws independent of the graph draw (perturbing one cannot move another)."""
    if pool is None:
        pool = hs.NEWS_POOL
    rng_s = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(hs.RNG_STREAM_NEWS_SCHEDULE,)))
    rng_c = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(hs.RNG_STREAM_NEWS_CONTENT,)))
    out = []
    for _ in range(int(n_rounds)):
        if float(rng_s.random()) < float(news_rate):
            out.append(pool[int(rng_c.integers(len(pool)))])
        else:
            out.append(None)
    return out


def _run_db_path(seed):
    """Unique per-(seed) run directory for the trace sqlite (a run ARTIFACT, never committed). Base
    is HARNESS_COHORT_DIR if set (the controller points it at the session scratchpad), else a stable
    subdir of the system temp. The db file is removed if stale so each run starts clean."""
    base = os.environ.get("HARNESS_COHORT_DIR") or os.path.join(
        tempfile.gettempdir(), "critaudit_cohort")
    run_dir = os.path.join(base, f"seed_{seed}")
    os.makedirs(run_dir, exist_ok=True)
    db_path = os.path.join(run_dir, "oasis.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    return db_path


def _make_counting_model(*, model_id, endpoint_url, token, max_tokens, temperature, timeout,
                         context_budget):
    """Build the cohort model backend on CAMEL's OPENAI_COMPATIBLE_MODEL client path
    (task9-rehearsal-report.md §3), wrapped in a thin driver-side subclass that SUMS per-call token
    usage across every model call. OASIS discards the ChatAgentResponse (env.step gathers but never
    collects _perform_llm_action's return, env.py:190-193), so usage is captured at the backend:
    the non-stream ChatCompletion returned by _arun/_run carries `.usage` (prompt/completion/total),
    the SAME field CAMEL itself reads for response.info['usage'] (chat_agent.py:2542-2544). Overriding
    the inner _run/_arun (not the public run/arun, which the base metaclass wraps + @observe
    decorates) captures every call including CAMEL's internal tool-loop repeats. Accumulation is
    synchronous (no await between the super() return and the += ), so OASIS's asyncio.gather
    per-round fan-out is race-free (single-threaded event loop, no interleave at the mutation).

    DECOUPLING (owner-ratified 2026-07-14, the seed-1 context-wall correction): CAMEL hardwires the
    agent CONTEXT budget to max_tokens (token_limit = model_config_dict.get("max_tokens") or ...,
    base_model.py:530-542) — one constant serving both the completion cap AND the memory budget is
    what drove prompt + 4096 past the served 8192 (1,021 silently-swallowed 400s, seed-1). The
    token_limit property is OVERRIDDEN to `context_budget` (= hs.COHORT_CONTEXT_BUDGET at the
    cohort) while requests keep max_tokens (= hs.COHORT_MAX_TOKENS, the measured completion cap);
    ChatAgent's context creator reads the override (chat_agent.py:478-481).

    LOUD-400 GUARD (part 1 of 2): OASIS swallows per-turn model errors (perform_action_by_llm
    catches ALL and returns the exception, agent.py:153-155), so server rejections are counted HERE:
    any raised error carrying a 4xx `status_code` (the openai.APIStatusError/BadRequestError shape —
    covers real vLLM 400s and synthetic test errors) increments `rejections` before re-raising.
    _run_oasis_minimal_async (part 2) raises at the first nonzero after every round.

    PER-CALL USAGE LOG (owner-ratified): `usage_log` records (prompt_tokens, completion_tokens) per
    call, so future anchors never depend on sums alone."""
    from camel.models.openai_compatible_model import OpenAICompatibleModel

    class _UsageAccountingModel(OpenAICompatibleModel):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.usage_counts = {"prompt": 0, "completion": 0, "total": 0, "n_calls": 0}
            self.usage_log = []          # per-call (prompt_tokens, completion_tokens)
            self.rejections = 0          # 4xx server rejections (the loud-400 guard reads this)

        @property
        def token_limit(self):
            # DECOUPLED context budget — NOT max_tokens (base_model.py:530-542 hardwires them).
            return context_budget

        def _count_rejection(self, exc):
            sc = getattr(exc, "status_code", None)
            if isinstance(sc, int) and 400 <= sc < 500:
                self.rejections += 1

        def _accumulate(self, result):
            self.usage_counts["n_calls"] += 1
            usage = getattr(result, "usage", None)
            p = int(getattr(usage, "prompt_tokens", 0) or 0) if usage is not None else 0
            c = int(getattr(usage, "completion_tokens", 0) or 0) if usage is not None else 0
            if usage is not None:
                self.usage_counts["prompt"] += p
                self.usage_counts["completion"] += c
                self.usage_counts["total"] += int(getattr(usage, "total_tokens", 0) or 0)
            self.usage_log.append((p, c))
            return result

        def _run(self, *a, **k):
            try:
                result = super()._run(*a, **k)
            except Exception as e:
                self._count_rejection(e)
                raise
            return self._accumulate(result)

        async def _arun(self, *a, **k):
            try:
                result = await super()._arun(*a, **k)
            except Exception as e:
                self._count_rejection(e)
                raise
            return self._accumulate(result)

    return _UsageAccountingModel(
        model_type=model_id,
        model_config_dict={"temperature": temperature, "max_tokens": max_tokens},
        api_key=token,
        url=endpoint_url,
        timeout=timeout,
    )


_NEWS_SENTINEL_MSG = ("news user is model-free by frozen NEWS_AUTHOR_RULE — a model call means a "
                      "driver bug routed an LLM action to it")


def _make_news_sentinel_model(*, model_id, endpoint_url, token, max_tokens, temperature, timeout,
                              context_budget):
    """FAIL-CLOSED sentinel backend for the manual news user (controller ratification 2026-07-14,
    strengthening the model=None correction): the frozen NEWS_AUTHOR_RULE "never LLM-driven" is
    ENFORCED at runtime, not assumed — sharing a live backend would let a driver bug that routes an
    LLMAction to the news user silently succeed and pollute authorship (same enforcement-over-
    assumption pattern as the parrot tripwire / positive-control gates). Constructed with the REAL
    endpoint config on the same OpenAICompatibleModel family, so every construction-time touch works
    (ChatAgent init -> ModelManager wrap; token_counter, openai_compatible_model.py:438; token_limit
    -> memory context creator, chat_agent.py:478-481) — but EVERY inference entry point raises.
    Coverage argument (verified from installed camel-ai 0.2.78): ChatAgent/ModelManager reach the
    backend ONLY via public run/arun (chat_agent.py:2184/2248/2838/3576; model_manager.py:229/274),
    which funnel to _run/_arun (base_model.py:428/480); the ONLY client-touching methods on
    OpenAICompatibleModel are the six _request_* helpers (openai_compatible_model.py:281-430), all
    called from _run/_arun — overridden too (belt-and-braces), so NO inference path escapes.
    `context_budget` mirrors the counting model's token_limit decoupling (constructor-consistency,
    owner-ratified 2026-07-14): construction-time touches see the same budget the crowd sees."""
    from camel.models.openai_compatible_model import OpenAICompatibleModel

    class _NewsSentinelModel(OpenAICompatibleModel):
        @property
        def token_limit(self):
            # same decoupling as the counting model (base_model.py:530-542 hardwires otherwise)
            return context_budget

        def _sentinel(self):
            raise AssertionError(_NEWS_SENTINEL_MSG)

        def _run(self, *a, **k):
            self._sentinel()

        async def _arun(self, *a, **k):
            self._sentinel()

        def _request_chat_completion(self, *a, **k):
            self._sentinel()

        async def _arequest_chat_completion(self, *a, **k):
            self._sentinel()

        def _request_parse(self, *a, **k):
            self._sentinel()

        async def _arequest_parse(self, *a, **k):
            self._sentinel()

        def _request_stream_parse(self, *a, **k):
            self._sentinel()

        async def _arequest_stream_parse(self, *a, **k):
            self._sentinel()

    return _NewsSentinelModel(
        model_type=model_id,
        model_config_dict={"temperature": temperature, "max_tokens": max_tokens},
        api_key=token,
        url=endpoint_url,
        timeout=timeout,
    )


def _new_user_info(*, name, bio, user_profile):
    """A UserInfo whose to_twitter_system_message uses name + profile.other_info.user_profile
    (config/user.py:50-63). recsys_type='twitter' selects the non-Reddit message form (independent
    of the Platform's recsys_type)."""
    from oasis.social_platform.config import UserInfo
    return UserInfo(
        name=name,
        description=bio,
        profile={"nodes": [], "edges": [], "other_info": {"user_profile": user_profile}},
        recsys_type="twitter",
    )


async def _run_oasis_minimal_async(*, operating_point, model, news_model, db_path, edges, schedule):
    """The awaited OASIS wiring (freeze report §4 ordered recipe). `model` is the crowd's counting
    backend; `news_model` is the news user's fail-closed sentinel; `edges`/`schedule` are the
    pure-builder outputs. Fail-closed: a failed follow insert raises (no silent partial graph)."""
    from oasis import (ActionType, AgentGraph, LLMAction, ManualAction, Platform,
                       SocialAgent, make)
    from oasis.social_platform.channel import Channel
    from oasis.social_platform.typing import RecsysType

    n_agents = int(operating_point["n_agents"])
    n_rounds = int(operating_point["n_rounds"])
    social_influence = int(operating_point["social_influence"])   # = refresh_rec_post_count knob
    available = [ActionType(name) for name in _MINIMAL_ACTION_NAMES]

    # 1. Build the graph: n_agents LLM crowd (ids 0..n_agents-1) + 1 manual news user (id n_agents).
    graph = AgentGraph()
    for i in range(n_agents):
        graph.add_agent(SocialAgent(
            agent_id=i,
            user_info=_new_user_info(name=f"user_{i}", bio=_CROWD_BIO,
                                     user_profile=_CROWD_USER_PROFILE),
            model=model, available_actions=available))
    news_id = n_agents          # NEWS_AUTHOR_RULE: id = n_agents (last graph member, excluded from
    #                             the crowd count); == hs.NEWS_USER_AGENT_ID at the frozen op-point.
    # NEWS-USER MODEL — verify-don't-relay correction of the freeze report's `model=None` claim,
    # RATIFIED with a strengthening (controller, 2026-07-14): model=None is NOT model-free here —
    # ChatAgent resolves None -> ModelFactory.create(DEFAULT = gpt-4.1-mini) -> OpenAI client, which
    # RAISES at construction without OPENAI_API_KEY (measured; chat_agent.py:595-600). The news user
    # gets the FAIL-CLOSED SENTINEL backend: its legitimate path is ManualAction only (env.step ->
    # perform_action_by_data -> the resolved SocialAction, NO model call, agent.py:278-294), and the
    # sentinel makes "never LLM-driven" a runtime tripwire — a driver bug routing an LLMAction to it
    # raises instead of silently emitting under news authorship. All four frozen NEWS_AUTHOR_RULE
    # properties hold (dedicated / never-LLM-driven [now ENFORCED] / no-follow-edges /
    # excluded-from-n_agents); token counts are unaffected (the sentinel can never be invoked).
    graph.add_agent(SocialAgent(
        agent_id=news_id,
        user_info=_new_user_info(name="news_source", bio=_NEWS_BIO,
                                 user_profile=_NEWS_USER_PROFILE),
        model=news_model, available_actions=available))

    # 2. Custom Platform (recsys_type frozen -> RecsysType enum; refresh_rec_post_count = the frozen
    #    coupling knob; max_rec_post_len >= that count so the knob is not silently capped). Passing
    #    recsys_type explicitly is REQUIRED (Platform default is "reddit", platform.py:64).
    platform = Platform(
        db_path=db_path,
        channel=Channel(),
        recsys_type=RecsysType(hs.RECSYS_TYPE),
        refresh_rec_post_count=social_influence,
        max_rec_post_len=MAX_REC_POST_LEN,
    )
    env = make(agent_graph=graph, platform=platform, database_path=db_path)

    # 3. Start platform + sign up all n_agents+1 members (env.reset -> generate_custom_agents).
    await env.reset()

    try:
        # 4. Realize the follow graph: sequential awaited SocialAction.follow in drawn order,
        #    post-reset pre-round-1, each mirrored into the in-memory graph (add_edge). DB `follow`
        #    row is the authoritative realized graph. Fail-closed on a failed insert.
        for (u, v) in edges:
            result = await graph.get_agent(u).env.action.follow(v)
            if not (isinstance(result, dict) and result.get("success")):
                raise RuntimeError(f"follow realization failed for edge ({u} -> {v}): {result!r}")
            graph.add_edge(u, v)

        # 5. Round loop r = 1..n_rounds: every LLM crowd agent acts via LLMAction; the news user is
        #    added to round r's SAME step dict with ManualAction(CREATE_POST) iff round r injects
        #    (submit-in-round-r, readable-from-r+1). REFRESH fires automatically inside each
        #    LLMAction. LOUD-400 GUARD (part 2, owner-ratified 2026-07-14): OASIS swallows per-turn
        #    model errors (agent.py:153-155) — the seed-1 wall produced 1,021 silent 400s and rounds
        #    of zero emits — so the rejection counter is checked after EVERY round and the run fails
        #    at rejection one, round granularity.
        news_agent = graph.get_agent(news_id)
        for r in range(n_rounds):
            actions = {graph.get_agent(i): LLMAction() for i in range(n_agents)}
            content = schedule[r]
            if content is not None:
                actions[news_agent] = ManualAction(
                    action_type=ActionType.CREATE_POST, action_args={"content": content})
            await env.step(actions)
            if model.rejections:
                raise AssertionError(
                    f"loud-400 guard: {model.rejections} server rejection(s) by end of round "
                    f"{r + 1}/{n_rounds} — the endpoint REJECTED requests (OASIS swallows per-turn "
                    f"errors; seed-1 precedent: context-wall 400s silently zeroed emits). "
                    f"Failing at rejection one, not at the end.")
    finally:
        # 6. Stop the platform task cleanly (also on a guard failure — no dangling platform task).
        await env.close()

    # Final belt (owner-ratified): a clean completion must have seen ZERO rejections.
    if model.rejections:
        raise AssertionError(
            f"loud-400 guard (final): {model.rejections} server rejection(s) over the run")


def run_oasis_minimal(seed, operating_point, model_id, endpoint_url, token):
    """OASIS-config integration (plan Task 10): build the frozen crowd at `operating_point`, run it
    through the OpenAI-compatible `endpoint_url` model `model_id`, and return
    (db_path, token_counts). All construction is dictated by the FROZEN rules in harness_spec +
    freeze report §4; see the module constants above for the disclosed Task-10 driver choices
    (max_rec_post_len=5, temperature=0.7). token_counts = {"prompt","completion","total","n_calls"}
    tallied by the driver-side accounting backend. The trace sqlite at db_path is a run artifact
    (never committed); export_harness_run(db_path, timestamp_col="created_at") reads it downstream."""
    import asyncio

    db_path = _run_db_path(seed)
    model = _make_counting_model(
        model_id=model_id, endpoint_url=endpoint_url, token=token,
        max_tokens=hs.COHORT_MAX_TOKENS, temperature=TEMPERATURE, timeout=CLIENT_TIMEOUT_S,
        context_budget=hs.COHORT_CONTEXT_BUDGET)
    news_model = _make_news_sentinel_model(
        model_id=model_id, endpoint_url=endpoint_url, token=token,
        max_tokens=hs.COHORT_MAX_TOKENS, temperature=TEMPERATURE, timeout=CLIENT_TIMEOUT_S,
        context_budget=hs.COHORT_CONTEXT_BUDGET)

    edges = build_follow_edges(
        seed, n_agents=operating_point["n_agents"], density=operating_point["network_density"])
    schedule = build_news_schedule(
        seed, n_rounds=operating_point["n_rounds"], news_rate=operating_point["news_rate"])

    asyncio.run(_run_oasis_minimal_async(
        operating_point=operating_point, model=model, news_model=news_model, db_path=db_path,
        edges=edges, schedule=schedule))

    token_counts = dict(model.usage_counts)
    return db_path, token_counts
