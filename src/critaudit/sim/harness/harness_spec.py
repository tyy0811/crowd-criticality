"""FROZEN, result-blind surface for the LLM-harness sub-increment 1. A change to a constant here is a
spec change, not a tweak. Thresholds are frozen from theory / input-side ranges BEFORE the reference
run — never back-filled from observed values. See docs/superpowers/specs/2026-06-27-llm-harness-subinc1-design.md.

READ->EMIT PAIRING RULE (frozen): an emit is a read->emit success iff its parent post is in the served
set of that agent's most-recent-prior REFRESH, where "prior" is by created_at (primary) with trace-rowid
breaking ties ONLY within the same created_at, never across rounds (OASIS's sandbox clock is round-granular;
ratified amendment 2026-06-30 — provenance: results/s2_harness/2026-06-29_task1_recon_pass_conditions.md +
DECISIONS.md 2026-06-30). read_emit_ratio = successes/events is the REALIZED fraction (<= n_struct < 1) —
it resolves read->emit ACCESSIBILITY only, NOT the crosses-1 generative n_emit (deferred; design §2/§12)."""
from __future__ import annotations

# --- positive-control thresholds (theory / Poisson-baseline; not back-filled) ---
READ_EMIT_FLOOR = 0.01     # read_emit_ratio must exceed this -> coupling present (some reads drive emits)
MAX_FRAC_SIZE1 = 0.95      # not ALL trees size-1 (a fully decoupled crowd is ~all size-1)
MAX_GIANT_FRAC = 0.90      # no single tree may swallow ~all events (degenerate one-component crowd)
LENGTH_SPREAD_FLOOR = 1.0  # message-length std (chars) > this -> content non-degenerate

# --- model (pinned for reproducibility; gate-model = sweep-model). Default starting rung. ---
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"   # 7-8B instruct, fits a single ~$1-2/hr Modal GPU (escalate per design §7)
MODEL_REVISION = "a09a35458c702b33eeacc393d103063234e8bc28"  # PINNED 2026-07-14 (plan Task 10 Step 1 —
#   the sanctioned mutation this line's original text ("PIN to a concrete commit hash ... before the
#   cohort run") carried): resolved from HF `main` 2026-07-14; == modal_serve.py SERVED_REVISION (the
#   revision actually SERVED and D0-verified by the Task-9 endpoint smoke, task9-rehearsal-report.md
#   §7-9); cross-file drift-guarded by test_task10_spec_freezes_present_and_sane.

# --- cohort seeds for the @slow positive-control run ---
COHORT_SEEDS = (20260627, 20260628, 20260629)

# --- coupling-dial construction (design §7, the riskiest freeze): the input-side knob realizing
#     "social-influence strength", plus the reference operating point, each value fixed RESULT-BLIND
#     from the INPUT side only (knob semantics + the knob's OWN documented range) — never from any n
#     it produces. Enumerated Task-7 by reading the INSTALLED camel-oasis 0.2.5 surface
#     (~/oasis_venv/lib/python3.11/site-packages/oasis/); the authoritative influence surface is the
#     Platform constructor (social_platform/platform.py:56-69). No native influence/strength/coupling
#     scalar exists in OASIS (grep-confirmed), so the axis is CONSTRUCTED from feed size exactly as
#     design §7 anticipated. Full enumeration table + selection argument: .superpowers/sdd/task-7-report.md.
#
#     SELECTED knob: refresh_rec_post_count (platform.py:65, `int = 1`) — "the number of posts returned
#     by the social media internal recommendation system per refresh" (doc comment platform.py:98-100).
#     It is the served recsys feed size: refresh() samples exactly this many rec-buffer posts per REFRESH
#     (platform.py:276-278) and the served set enters the agent prompt verbatim ("After refreshing, you
#     see some posts", agent_environment.py:37-63 -> perform_action_by_llm agent.py:127-134). Among the
#     exposed knobs it most directly IS "how strongly neighbour content drives an agent". Rejected (less
#     direct): following_post_count (platform.py:67) = served follow-network feed, CONFOUNDED with the
#     separately-frozen network_density axis (gated by the `follow` table, platform.py:280-298) and
#     non-Reddit-only; max_rec_post_len (platform.py:66) = rec-buffer/candidate cap, one indirection
#     UPSTREAM of the served feed (refresh samples FROM it), not what the agent reads; recsys_type
#     (typing.py:81-85, enum {twitter,twhin-bert,reddit,random}) = algorithm choice, no principled
#     input-side ordering of "strength"; rec_prob (platform.py:108) is DEAD (set once, never read);
#     swap_rate (recsys.py:688) is not plumbed through Platform (update_rec_table omits it); "prompt
#     susceptibility" is free-text profile only (config/user.py) — none is an exposed settable scalar.
#
#     MID-RANGE value (result-blind, from the knob's OWN documented values — NOT from any produced n):
#     OASIS ships refresh_rec_post_count at 1 (Platform default platform.py:65), 2 (DefaultPlatformType
#     .TWITTER env.py:82), 5 (DefaultPlatformType.REDDIT env.py:96) -> documented span [1, 5]; arithmetic
#     midpoint (1+5)/2 = 3. (A count's only natural upper bound is the buffer max_rec_post_len, so the
#     bounded range used is OASIS's own documented shipped span; basis alternatives — median{1,2,5}=2,
#     buffer-relative — disclosed in the report and ratified as a genuinely free result-blind choice.)
#
#     RATIFIED by owner 2026-07-13 (DECISIONS.md 2026-07-13) with this SCOPING CAVEAT: the knob's axis is
#     EXPOSURE VOLUME. "More posts served = stronger effective coupling" is a MECHANISM ASSUMPTION, not a
#     fact — more served content could in principle dilute attention rather than amplify drive. The sweep
#     itself reveals the actual exposure->coupling mapping; downstream interpretation must NOT treat
#     monotonicity as built-in when it was assumed. (This scopes what the knob is KNOWN to be — served-feed
#     width — without weakening the selection.)
COUPLING_KNOB = "refresh_rec_post_count"   # OASIS Platform ctor arg (platform.py:65); carries `social_influence`
OPERATING_POINT = {
    # Each value is a registered mid-range intent (2026-06-27) or the knob's own documented mid-range;
    # zero output-side reasoning anywhere. The trailing note per key is the WIRING: the exact OASIS
    # surface Task 9/10 `run_oasis_minimal` sets it through (so no re-enumeration is needed downstream).
    #
    # DEFERRED-FREEZE OBLIGATION (owner ratification 2026-07-13): network_density and news_rate are
    # ratified as harness-CONSTRUCTED build items ONLY — that ratification does NOT pre-ratify their
    # eventual construction rules or realized values. The Task-9/10 construction rules (the exact
    # follow-edge-fraction realization; the injection schedule) MUST be frozen result-blind BEFORE any
    # cohort output exists — the same standard COUPLING_KNOB met. Constructing an axis risks selecting
    # the axis on the quantity under test (the adopt-OASIS warning attaches exactly here). Phase B may
    # not read this dict as "already ratified" for those two keys' realizations.
    #   DISCHARGED 2026-07-14 by the NETWORK_CONSTRUCTION + NEWS_INJECTION block appended below
    #   (result-blind, pre-output; DECISIONS.md 2026-07-13 Ratification 2).
    "n_agents": 50,            # crowd size -> number of SocialAgents in the AgentGraph passed to make()
                               #   (= profile row count / agent_graph.add_agent calls;
                               #   generate_twitter_agent_graph, agents_generator.py:614-649)
    "n_rounds": 20,            # number of OasisEnv.step() calls in the driver loop (1 step = 1 round;
                               #   Twitter clock ticks per step, env.py:197-198)
    "network_density": 0.10,   # fraction of directed follow-edges: harness builds ~0.10*n*(n-1) follow rows
                               #   (profile following-list / agent_graph.add_edge -> `follow` table, read at
                               #   refresh platform.py:285-298). OASIS exposes NO density scalar -> realized
                               #   profile-carried (faithful, not reinterpreted; see report rule-5 check).
    "news_rate": 0.05,         # per-round P(inject one exogenous news post) via a driver-issued
                               #   ManualAction(ActionType.CREATE_POST) (handled OasisEnv.step, env.py:160-188).
                               #   OASIS exposes NO native news scalar -> realized driver-carried (faithful).
    "social_influence": 3,     # = COUPLING_KNOB mid-range -> Platform(refresh_rec_post_count=3) (platform.py:65)
}

# --- constructed-axis freezes (Phase B; discharges the DEFERRED-FREEZE OBLIGATION above): the
#     harness-side construction rules realizing network_density and news_rate, frozen result-blind
#     2026-07-14 BEFORE any cohort output exists (DECISIONS.md 2026-07-13 Ratification 2). No OASIS
#     run, no LLM call, no output-side quantity informed any element below; every feasibility claim
#     carries file:line provenance from the INSTALLED camel-oasis 0.2.5 source
#     (~/oasis_venv/lib/python3.11/site-packages/oasis/). Full fork-by-fork arguments, alternatives
#     tables and the exact Task-9/10 wiring contract: .superpowers/sdd/phaseB-freeze-report.md.
#
#     SHARED SEEDING CONVENTION (namespaced independent streams): stream k of a cohort member is
#     numpy.random.default_rng(numpy.random.SeedSequence(cohort_seed, spawn_key=(k,))) — numpy's
#     documented independent-stream mechanism, so changing consumption in one stream cannot perturb
#     another (the graph draw and the news draws are decoupled by construction). Additive-offset
#     seeding (cohort_seed + k) is REJECTED on an input-side fact, not taste: COHORT_SEEDS are
#     consecutive integers, so any small additive offset collides across cohort members
#     (20260627 + 1 == 20260628 + 0); spawn-key namespacing cannot collide. Stream-index labels
#     themselves are a disclosed convention (any fixed distinct ints would do).
RNG_STREAM_GRAPH = 0          # follow-graph draw
RNG_STREAM_NEWS_SCHEDULE = 1  # per-round news Bernoulli draws (consumed in round order 1..n_rounds)
RNG_STREAM_NEWS_CONTENT = 2   # pool-index draw per realized injection (consumed in injection order)

# --- NETWORK_CONSTRUCTION (network_density = 0.10 -> follow edges), frozen result-blind ---------
#     FORM: exact-count directed G(n, M): M = round(density * n * (n-1)) DISTINCT ordered pairs
#     (u, v), u != v, drawn uniformly WITHOUT replacement over the LLM-crowd ids 0..n_agents-1
#     (operating point: round(0.10 * 50 * 49) = 245 exactly; round() is Python round-half-even —
#     disclosed, moot at the frozen point). Pair space enumerated lexicographically
#     (index i -> u = i // (n-1); r = i % (n-1); v = r if r < u else r + 1), sampled via
#     rng.choice(n*(n-1), size=M, replace=False) on the RNG_STREAM_GRAPH stream — the edge set is
#     a pure function of the cohort seed.
#       INPUT-SIDE DISCRIMINATOR vs per-pair Bernoulli G(n, p) (the textbook null model, disclosed
#     alternative): density is ITSELF the sweep axis; exact-count makes the constructed INPUT
#     deterministic-in-count per seed — zero run-to-run density variance enters the axis, whereas
#     G(n, p) jitters the realized count (sd = sqrt(M(1-p)) ~ 14.9 edges, ~6% relative at the
#     operating point — arithmetic on frozen constants), injecting input noise downstream-
#     indistinguishable from dynamical response. G(n, M) IS G(n, p) conditioned on the count, so
#     no structure is sacrificed. Symmetrized/mutual-follow graphs also disclosed and rejected:
#     OASIS follow edges are natively DIRECTED (follower_id -> followee_id row, platform.py:881-884;
#     igraph directed=True, agent_graph.py:185) and the registered intent names "directed
#     follow-edges". SELF-LOOPS: excluded by THIS rule (u != v; the n*(n-1) denominator says so) —
#     Platform.follow has only a duplicate check, no self-follow guard (platform.py:868-877), so
#     the exclusion must live harness-side. RECIPROCITY: not imposed; (u,v) and (v,u) are
#     independent ordered pairs, mutual dyads occur at the null-model rate.
#     REALIZATION SURFACE (the named surface run_oasis_minimal drives): awaited SocialAction.follow
#     calls — graph.get_agent(u).env.action.follow(v) (agent_action.py:395-412 -> Platform.follow:
#     dup-check, INSERT INTO follow(follower_id, followee_id, created_at), counters, trace row;
#     platform.py:859-914) — issued SEQUENTIALLY in drawn order AFTER env.reset() and BEFORE the
#     first env.step(), each mirrored into the in-memory graph via agent_graph.add_edge(u, v)
#     (agent_graph.py:206-210) — the follow()+add_edge idiom OASIS itself uses at SETUP time for
#     control agents (agents_generator.py:384-385, the live precedent). CORRECTED 2026-07-14
#     (review catch, re-verified from source): OASIS maintains NO runtime graph/DB invariant —
#     the runtime mirror perform_agent_graph_action (agent.py:296-317) is DEAD CODE in
#     camel-oasis 0.2.5 (its only caller is commented out, agent.py:150; grep-confirmed no other
#     caller), so LLM-driven follows during rounds write the DB follow table but are NOT
#     mirrored to the igraph: as rounds run, the igraph holds construction edges only and
#     DIVERGES from the DB. The DB row is the authoritative realized graph — Task 9/10 must
#     NEVER read the igraph as the realized follow graph. Refresh serves follow content from the
#     follow TABLE (post JOIN follow ... WHERE follow.follower_id = ?, platform.py:283-296).
#       WHY THIS SURFACE (source-verified; supersedes the OPERATING_POINT wiring note's
#     anticipated "profile following-list / add_edge" family with the pipe that actually exists):
#     env.reset() -> generate_custom_agents ONLY signs agents up — it reads NO graph edges and
#     inserts NO follow rows (agents_generator.py:547-564; env.py:121-122), so in-memory add_edge
#     alone never reaches the DB; the CSV profile route (following_agentid_list -> batch INSERT,
#     agents_generator.py:120-128, 146-151) belongs to the legacy generate_agents entry point,
#     not the AgentGraph+reset flow the harness uses. perform_action_by_data(FOLLOW) REJECTED for
#     edge seeding: it writes a synthetic action record into the agent's LLM memory
#     (agent.py:286-291) — construction leaking into prompts; the bare SocialAction surface is
#     memory-clean and is OASIS's own reset-time idiom (sign_up is driven exactly so,
#     agents_generator.py:557-563). Direct DB INSERT rejected as off-surface (no trace row, no
#     counters). Pre-round follow rows carry created_at = tick "0" (clock starts at 0, clock.py:23;
#     ticks only inside env.step, env.py:197-198); they are neither REFRESH nor emit rows, so the
#     frozen pairing rule is untouched.
#     SCOPE CONSTRAINT (recorded, not a new freeze): follow-content serving fires only for
#     recsys_type != REDDIT (platform.py:280), which the frozen round-granular pairing rule
#     already presupposes (non-Reddit clock get_time_step, platform.py:264). recsys_type itself
#     remains a separate, still-open Task-9/10 result-blind freeze.
NETWORK_GRAPH_FORM = "directed_gnm_exact_count"   # M = round(density*n*(n-1)) ordered pairs, u != v, uniform w/o replacement
NETWORK_EDGE_SURFACE = "SocialAction.follow"      # post-reset pre-round-1 sequential awaits + agent_graph.add_edge mirror

# --- NEWS_INJECTION (news_rate = 0.05 -> exogenous posts), frozen result-blind ------------------
#     SCHEDULE: independent Bernoulli(news_rate) per round r = 1..n_rounds on the
#     RNG_STREAM_NEWS_SCHEDULE stream (ONE uniform per round, consumed in round order): at most
#     one news post per round — the registered intent's literal form ("per-round P(inject one
#     exogenous news post)"). ALL rounds eligible, including the last (constant per-round rate;
#     truncating final-round eligibility would make the rate round-dependent — the boundary
#     injection never being readable is a horizon fact, not a rate change). Alternatives
#     disclosed: per-round Poisson (rejected: admits 2+ posts/round, deviating from the
#     registered one-post form); deterministic every-1/rate schedule (rejected: replaces the
#     registered probabilistic rate with a schedule).
#     TIMING / READABILITY (source-decided): the round-r injection is submitted as ONE extra
#     entry in the SAME env.step(actions) dict as round r's LLM actions —
#     {news_agent: ManualAction(ActionType.CREATE_POST, {"content": <draw>})} (ManualAction,
#     env_action.py:20-37; create_post arg name "content", agent_action.py:145). env.step
#     rebuilds the rec table BEFORE executing any action of the round (env.py:151-152) and runs
#     the round's actions CONCURRENTLY (asyncio.gather, env.py:193), so a round-r news post is
#     NOT reliably readable in round r (the rec buffer predates it; within-round order is
#     unordered) and IS deterministically in the recsys candidate pool from round r+1 on
#     (update_rec_table rebuilds from the full post table, platform.py:328-397; candidate pools
#     draw platform-globally: rec_sys_random recsys.py:152, personalized-with-trace
#     recsys.py:719-729). FROZEN: submit-in-round-r, readable-from-round-r+1 — a uniform
#     one-round latency, an input-side property of the platform, identical for every injection.
#     The dispatch-anticipated "round-start injection readable same round" is NOT source-
#     supported and is therefore not frozen. Alternative disclosed: a dedicated news-only
#     env.step before each round would be readable same-round but is REJECTED on two source
#     grounds: every step ticks the sandbox clock (env.py:197-198), making round/clock
#     bookkeeping depend on the news draw (perturbing the frozen created_at-primary pairing
#     rule's round semantics), and it doubles update_rec_table on injection rounds, leaking the
#     news axis into the coupling axis's served-feed state.
#     AUTHOR: a DEDICATED manual news user — graph id n_agents, one past the last LLM-crowd id
#     (the graph carries n_agents+1 members; OPERATING_POINT["n_agents"] remains the LLM-crowd
#     count). Signed up like any graph member (env.reset -> generate_custom_agents signs up EVERY
#     member, agents_generator.py:557-563; user_id = agent_id, platform.py:186-195). It holds NO
#     follow edges in either direction — outside the network draw's 0..n_agents-1 pair space —
#     because follow-reach would make news exposure depend on the drawn graph (coupling the two
#     constructed axes) and news would crowd the like-ranked width-limited follow feed
#     (platform.py:290-296); its reach is exclusively the platform-global rec pool. It is NEVER
#     LLM-driven: the driver lists it in an actions dict only on injection rounds and only with
#     ManualAction — env.step dispatches non-interview ManualActions to perform_action_by_data
#     (env.py:160-188), which resolves the SocialAction wrapper and awaits it with NO model call
#     (agent.py:278-294; model is Optional, agent.py:58-65, and the manual path bypasses
#     available_actions, agent.py:281); precedent: the Task-1 recon fixture's manual repost.
#     Its posts are ordinary root posts (create_post -> original_post_id NULL) and REMAIN in the
#     exported event stream — they are the exogenous immigrants the axis exists to supply.
#     CONTENT (frozen NOW, not at run time: content enters agent prompts via refresh and
#     run.content via the exporter, hence the length_spread diagnostic — a post-hoc content
#     choice is exactly the tuning channel this freeze closes): each injection draws uniformly
#     WITH replacement from NEWS_POOL on the RNG_STREAM_NEWS_CONTENT stream (with-replacement is
#     defined for any injection count with no wrap rule; repeating a neutral string is input-side
#     harmless — shuffle-without-replacement disclosed as the alternative). The pool: 12
#     topic-neutral, declarative, OASIS-plausible one-liners — no questions, no calls-to-action,
#     no hashtags, no @mentions (minimal prompt-steering surface); pool size and exact wording
#     are a disclosed convention choice (sanctioned range 8-16). All 12 strings AND all 12
#     lengths are distinct (64-101 chars, std ~12.1 > LENGTH_SPREAD_FLOOR), so the news
#     contribution to length_spread is non-degenerate; expected injections at the operating
#     point = n_rounds * news_rate = 1 (arithmetic on frozen constants), so the diagnostic
#     remains crowd-dominated.
NEWS_SCHEDULE_FORM = "bernoulli_per_round_at_most_one__submit_round_r_readable_from_r_plus_1"
NEWS_AUTHOR_RULE = "dedicated_manual_user__never_llm_driven__no_follow_edges__excluded_from_n_agents"
NEWS_USER_AGENT_ID = OPERATING_POINT["n_agents"]  # = 50 at the frozen point; rule: id = n_agents (last graph member)
NEWS_POOL = (
    "Volunteers finish the riverside trail cleanup ahead of schedule.",
    "Historical society digitizes a small collection of early city maps and ferry timetables.",
    "Astronomers report a newly catalogued comet expected to be visible with binoculars late next month.",
    "Regional transit authority adds two early-morning weekday routes.",
    "City council approves funding to renovate the central library reading room and its archive annex.",
    "Botanic garden announces that its annual seed exchange will open to the public next week.",
    "Local museum extends the natural history exhibit through the end of the season.",
    "Researchers publish a multi-year survey of migratory bird patterns recorded along the northern coast.",
    "Community orchestra schedules an open-air concert at the park pavilion.",
    "Weather service forecasts a mild week with light rain arriving toward the weekend.",
    "University lab reports steady progress on a low-cost water filtration method for rural wells.",
    "Archaeology team completes cataloguing of artifacts recovered from last summer's dig.",
)

# --- Task-10 spec freezes (2026-07-14, result-blind): RECSYS_TYPE + COHORT_MAX_TOKENS ------------
#     (MODEL_REVISION pinned above per plan Task 10 Step 1 — the one sanctioned non-append edit;
#     the constant's own original comment carried that obligation.) Everything below is input-side
#     only; provenance = installed camel-oasis 0.2.5 + camel-ai 0.2.78 + the Task-9 rehearsal's
#     INSTRUMENT-HEALTH facts (.superpowers/sdd/task9-rehearsal-report.md). No cohort ran; no
#     output-side statistic informed any value. Recsys obligation: DECISIONS.md 2026-07-13 /
#     the NETWORK_CONSTRUCTION scope-constraint above ("still-open Task-9/10 result-blind freeze").
#
#     RECSYS_TYPE — which recommender fills the rec buffer the coupling knob samples from
#     (refresh serves refresh_rec_post_count posts sampled FROM the rec table, platform.py:276-278).
#     WHERE PASSED (source-verified): the Platform ctor arg `recsys_type` (platform.py:64) —
#     whose DEFAULT IS "reddit", so run_oasis_minimal MUST pass this value explicitly —
#     normalized via RecsysType(...) at platform.py:88; OasisEnv then derives the TWITTER-family
#     platform_type for any non-Reddit value (env.py:109-112) -> per-step clock tick
#     (env.py:197-198) = the round-granular created_at the frozen pairing rule requires.
#     Enum surface (typing.py:81-85) with the update_rec_table dispatch, all four verified:
#       "reddit"     -> rec_sys_reddit (platform.py:376-378). DISQUALIFIED (a): under REDDIT,
#                       refresh SKIPS the follow-feed join (platform.py:280) — kills the frozen
#                       network axis — and the clock is real-time, not round-granular
#                       (platform.py:260-262), breaking the frozen pairing rule.
#       "twitter"    -> rec_sys_personalized_with_trace (platform.py:339-342). DISQUALIFIED (b),
#                       KNOWN DEFECT, source-verified: the builder emits len(rec_matrix)-1 rows
#                       positioned by user_table order (recsys.py:719-726) while update_rec_table
#                       writes rows back keyed by bare range(len(...)) AS user_ids
#                       (platform.py:388-395) — inconsistent builder/writer conventions. Under
#                       the helper's own documented 1-based-ids assumption (database.py:258-259)
#                       every row lands one user off; under this harness's 0-based layout the
#                       LAST user is silently dropped and the row<->user mapping additionally
#                       rests on an unordered SELECT (fetch_table_from_db has no ORDER BY,
#                       database.py:249-254). Also silently fixes swap_rate (unplumbed;
#                       Task-7 enumeration row 6).
#       "twhin-bert" -> rec_sys_personalized_twh (platform.py:343-375). DISQUALIFIED (c): loads
#                       the Twitter/twhin-bert-base embedding model via transformers
#                       from_pretrained (recsys.py:64-93; SentenceTransformer import
#                       recsys.py:27) — model substrate BEYOND the pinned LLM (extra weights
#                       download at cohort time, freshly-initialized pooler weights observed in
#                       the Task-9 rehearsal = new nondeterminism, network dependency;
#                       use_openai_embedding would add a PAID API, contra the budget reality).
#       "random"     -> rec_sys_random (platform.py:336-338). SELECTED: platform-global uniform
#                       candidate pool (post_ids from the FULL post table, recsys.py:152-163) —
#                       the news channel reaches every agent exactly as the NEWS_INJECTION
#                       freeze requires; builder/writer convention-SAFE (emits exactly
#                       len(rec_matrix) rows of user-independent content, so the range()
#                       write-back cannot misattribute rows); ZERO extra substrate; and it keeps
#                       the coupling axis clean — exposure width (refresh_rec_post_count) sweeps
#                       over a neutral uniformly-filled buffer with no similarity-ranking layer
#                       confounding "how much is served".
#     KNOWN NONDETERMINISM, recorded honestly (rule d): rec_sys_random draws with the UNSEEDED
#     stdlib module RNG (import random, recsys.py:18; random.sample, recsys.py:163), as does
#     refresh's own buffer subsample under EVERY recsys type (platform.py:277-278). OASIS-internal
#     sampling is therefore NOT seed-reproducible from the harness side; the constructed INPUTS
#     (graph, news) remain exactly reproducible via the namespaced streams above, and the LLM
#     samples at temperature — the cohort's reproducibility boundary is inputs-deterministic /
#     dynamics-stochastic. Do not pretend otherwise downstream.
#     WIRING CAUTION for the Platform build (recorded here because it can silently unbind the
#     frozen knob): Platform's default max_rec_post_len = 2 (platform.py:66) is SMALLER than the
#     frozen refresh_rec_post_count = 3, and refresh's sample branch fires only when the buffer
#     has >= refresh_rec_post_count entries (platform.py:276-278) — with the default, at most 2
#     rec posts are ever served and the frozen operating point is silently capped. Task 10's
#     Platform(...) call must set max_rec_post_len >= refresh_rec_post_count (OASIS's own Reddit
#     preset uses 100 vs 5, env.py:95-96); the exact value is a Task-10 driver choice to be set
#     result-blind there, not a new spec constant here.
RECSYS_TYPE = "random"   # exact string run_oasis_minimal passes: Platform(recsys_type=RECSYS_TYPE) (platform.py:64)

#     COHORT_MAX_TOKENS — instrument-integrity constant, consumed as model_config_dict
#     ["max_tokens"] in the cohort's ModelFactory.create(...) on the OPENAI_COMPATIBLE_MODEL
#     client path (task9-rehearsal-report.md §3). CAMEL couples this value to the agent CONTEXT
#     budget: BaseModelBackend.token_limit = model_config_dict.get("max_tokens") or the library's
#     own per-model default (camel base_model.py:539-542), and ChatAgent feeds token_limit into
#     its memory context creator (camel chat_agent.py:478-481) — too small and the OBSERVATION
#     (the refresh-served posts) is truncated out of the prompt: the read channel breaks UPSTREAM
#     of any measurement. Task-9 $0 rehearsal measured the instrument-health fact: at 512,
#     pervasive CAMEL context-truncation warnings ("Context truncation performed: before=1720,
#     after=497, limit=512" — observations sliced); at 4096 on the endpoint smoke, ZERO
#     truncation warnings (grep-confirmed; report §5.3/§9). The discriminating evidence is the
#     truncation warnings ONLY (prompt integrity, like D0) — no emitted-stream statistic informed
#     this value: it repairs a broken instrument, it does not tune one. Upper bound: the endpoint
#     serves --max-model-len 8192 (modal_serve.py:118); 4096 leaves prompt headroom under the
#     serving cap. Alternative disclosed: omit max_tokens entirely -> CAMEL falls back to its own
#     model-table token_limit — rejected: a cohort-substrate value must be REGISTERED in the
#     spec, not inherited from a library default that can drift on a camel upgrade.
#
#     SUPERSEDED 2026-07-14 (owner-ratified correction-by-provenance; sanctioned mutation): the
#     4096 above was authored UNDER the coupling constraint — CAMEL hardwires the agent CONTEXT
#     budget to max_tokens (token_limit = model_config_dict.get("max_tokens") or ...,
#     base_model.py:530-542) — BEFORE that substrate fact was known, so one constant was forced to
#     serve BOTH the completion cap and the memory budget and was sized for the budget role.
#     EVIDENCE (seed-1, 20260627): prompts grew to the 4096 wall by round ~5, then
#     prompt + 4096 completion allowance exceeded the served --max-model-len 8192 -> 1,021 vLLM
#     400-rejections, silently swallowed by OASIS's per-turn catch (emit histogram 18/48/49/14/3
#     then zeros; rejection bodies censored at the validation threshold, value=4097 — hence the
#     constructive Measurement 2 below, not log-mining). The driver now DECOUPLES the roles
#     (token_limit override in oasis_adapter's model subclasses): COHORT_MAX_TOKENS is ONLY the
#     per-request completion cap; COHORT_CONTEXT_BUDGET below is the memory budget.
#     MEASURED ANCHOR (Measurement 1, 2026-07-14, offline, seed-1 trace read-only): ALL 164
#     successful LLM tool calls (23 create_post + 94 create_comment + 2 repost + 13 quote_post +
#     32 do_nothing) reconstructed in the PINNED tokenizer's own hermes tool-call rendering
#     ('<tool_call>\n{"name":...,"arguments":...}\n</tool_call>' + <|im_end|>) and tokenized at
#     the pinned revision -> n=164, mean 41.3, p99 56.1, MAX 59 tokens (top-5: 59/58/55/55/55).
#     Owner cap rule: "512 >= 2x observed max" FIRES (512 >= 118) -> 512, basis: clears the
#     observed max (59 tokens) by 8.7x. Full tables: .superpowers/sdd/task10-driver-report.md §10.
COHORT_MAX_TOKENS = 512

#     COHORT_CONTEXT_BUDGET — the CLIENT-SIDE context budget: what ChatAgent's ScoreBasedContext-
#     Creator trims agent memory to (chat_agent.py:478-481), fed by the driver's token_limit
#     override (decoupled from COHORT_MAX_TOKENS, which stays the request's completion cap).
#     Frozen 2026-07-14 from OFFLINE measurements only (no GPU/endpoint; both arithmetic terms
#     OBSERVED, none estimated — the owner's ratification condition):
#       Measurement 2 (constructive worst case): the ACTUAL client counter is
#       OpenAITokenCounter(GPT_4O_MINI) (openai_compatible_model.py:437-448; o200k_base encoding,
#       +3/message + role tokens + final +3, token_counting.py:118-230). Synthetic histories tuned
#       so THAT counter counts EXACTLY B; server side = pinned Qwen tokenizer
#       apply_chat_template(msgs, tools=<the REAL 5 minimal-action schemas via the driver's
#       FunctionTool path>, add_generation_prompt=True). overhead(B) = server - B, over
#       B in {5632, 6144} x 3 adversarial shapes:
#         few-large +820 | many-small +832 | oasis-rounds (19 tool-call turns) +1731 (both B)
#       -> overhead_max = 1731. Decomposition (all observed): 696 fixed tool-schema tokens (the
#       client counter never counts tools); +1/msg template delta (server 5 vs client 4);
#       +2.37% qwen-vs-o200k content mismatch; +51/turn assistant tool-call under-count (the
#       client counts a tool_calls list as ~0, the server renders the full call JSON) x 19 turns.
#     DERIVATION (verbatim): COHORT_CONTEXT_BUDGET = the largest multiple of 512 satisfying
#       B + overhead_max(B) + COHORT_MAX_TOKENS + 256 slack <= 8192 (served --max-model-len):
#         B=6144: 6144 + 1731 + 512 + 256 = 8643 >  8192 -> FAIL
#         B=5632: 5632 + 1731 + 512 + 256 = 8131 <= 8192 -> PASS
#       (256 = safety slack, DECLARED — the one non-measured term.)
COHORT_CONTEXT_BUDGET = 5632

#     OVERHEAD_MAX_MEASURED — the constructive Measurement-2 maximum overhead (shape C,
#     oasis-rounds with 19 tool-call turns; identical at B=5632 and B=6144), measured 2026-07-14;
#     promoted to a named frozen constant (reviewer hardening) so the consumed-guard can enforce
#     the FULL derivation inequality (budget + overhead + cap + slack <= served --max-model-len)
#     rather than a weaker necessary condition — a future budget change cannot pass the guard while
#     violating the real constraint. RE-MEASURE TRIGGER: any change to the per-round memory shape
#     (message mix, multi-tool-call turns) or to the tool schemas (action set, signatures,
#     docstrings) invalidates this maximum — re-run Measurement 2
#     (.superpowers/sdd/task10-driver-report.md §10.2) and re-derive before relying on the guard.
OVERHEAD_MAX_MEASURED = 1731

#     FINITE-MEMORY-HORIZON (declared property of the frozen recipe; same status as the
#     exposure-volume caveat on COUPLING_KNOB): with a finite context budget, late-round agents
#     TRUNCATE their oldest messages — the crowd has a memory horizon BY CONSTRUCTION. Memory
#     truncation can plausibly shape cascade statistics (agents forgetting early posts changes
#     what they can still reply to). Declared NOW as an assumption surface of the harness; it must
#     not be discovered later as an unrecorded confound. Downstream interpretation of cascade/tree
#     statistics inherits this property.
