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
#     bounded range used is OASIS's own documented shipped span; owner-ratification caveat in the report.)
COUPLING_KNOB = "refresh_rec_post_count"   # OASIS Platform ctor arg (platform.py:65); carries `social_influence`
OPERATING_POINT = {
    # Each value is a registered mid-range intent (2026-06-27) or the knob's own documented mid-range;
    # zero output-side reasoning anywhere. The trailing note per key is the WIRING: the exact OASIS
    # surface Task 9/10 `run_oasis_minimal` sets it through (so no re-enumeration is needed downstream).
    "n_agents": 50,            # crowd size -> number of SocialAgents in the AgentGraph passed to make()
                               #   (= profile row count / agent_graph.add_agent calls; agents_generator.py)
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
