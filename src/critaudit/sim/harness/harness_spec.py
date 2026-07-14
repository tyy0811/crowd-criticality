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
MODEL_REVISION = "main"                   # PIN to a concrete commit hash at Task 9 before the cohort run

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
