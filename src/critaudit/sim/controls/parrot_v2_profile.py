"""Task 3 (Branch-B parrot-null v2 implementation plan, 2026-07-31): whitelisted, hash-pinned
per-window action-profile extraction — the surface through which ONE registered cohort window's
action composition reaches the matched generator for parrot-null v2.

`CohortActionProfile` REPLICATES the `cohort_marginals.py` structural-firewall pattern (a
whitelisted frozen dataclass + a module-level field-set tuple pinned by an assert): deliberately a
different, wider whitelist than `CohortMarginals` (per-round TYPE counts, refresh counts, news
events, and the authored-text pool, rather than just aggregate counts + text) — cohort_marginals.py
itself is NOT imported or modified; the pattern is copied, not reused, so this module's whitelist
can never silently drift onto that module's frozen surface or vice versa.

Extraction consumes the Task-1 shared loader triple directly
(`critaudit.sim.harness.oasis_adapter.load_harness_records`) rather than the assembled/validated
`HarnessRun` — the loader alone performs NO parent-chain validation, which is fine here because
counts and the authored-text pool never need parent structure. `action_by_item` (item_id -> traced
emit action name) is the type-discrimination source; an item absent from that map has no trace row,
which is a create_post root (untraced seed post) per the loader's own contract."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields

from critaudit.sim.harness.harness_spec import NEWS_USER_AGENT_ID
from critaudit.sim.harness.oasis_adapter import load_harness_records

# The four traced emit action names, in the fixed column order `per_round_type_counts` reports.
ACTION_TYPES = ("create_post", "create_comment", "repost", "quote_post")


@dataclass(frozen=True)
class CohortActionProfile:
    """The action-profile of ONE registered cohort window, whitelisted (structural firewall,
    mirroring cohort_marginals.py's CohortMarginals). Fields:

    - window_seed: the cohort seed the profile was extracted for.
    - per_round_type_counts: tuple over rounds of 4-tuples (create_post, create_comment, repost,
      quote_post) — NEWS-ADJUSTED BY DEFINITION: each news-user event (agent_id ==
      NEWS_USER_AGENT_ID) subtracts 1 from its own round's create_post count (news events are
      traced create_post rows; the adjustment removes the exogenous immigrant from the crowd's own
      action-type composition).
    - per_round_refresh_counts: tuple[int] over rounds, traced refreshes only.
    - news_events: tuple of (round, content) for every news-user event, in stream order.
    - authored_corpus: tuple of authored texts of non-news, non-repost events, in stream order
      (repost '' entries and news text are EXCLUDED — a repost carries no authored text and news
      is the exogenous immigrant, not part of the crowd's authored pool)."""
    window_seed: int
    per_round_type_counts: tuple
    per_round_refresh_counts: tuple
    news_events: tuple
    authored_corpus: tuple


# The whitelist this module pins — change requires a spec change, loudly (cohort_marginals.py's
# own firewall test pins its sibling whitelist the same way; this is the independent copy for the
# wider action-profile surface).
COHORT_ACTION_PROFILE_FIELDS = (
    "window_seed", "per_round_type_counts", "per_round_refresh_counts",
    "news_events", "authored_corpus")
assert tuple(f.name for f in fields(CohortActionProfile)) == COHORT_ACTION_PROFILE_FIELDS


def _round_of(time_value, *, kind):
    """Round index for ONE event/refresh time: int(time_value), fail-closed on non-integral or
    negative (mirrors the round_indices discipline in cohort_marginals.py — replicated per-value
    here rather than imported, since this module never imports cohort_marginals.py)."""
    rounded = int(time_value)
    if rounded != time_value:
        raise ValueError(
            f"extract_action_profile: non-integral {kind} time {time_value!r} — round semantics "
            f"undefined (fail-closed)")
    if rounded < 0:
        raise ValueError(f"extract_action_profile: negative {kind} round {rounded} (fail-closed)")
    return rounded


def extract_action_profile(db_path, *, window_seed):
    """Extract the CohortActionProfile of one registered cohort window from its OASIS trace DB.

    Consumes `load_harness_records(db_path, timestamp_col="created_at")` (the Task-1 triple)
    directly: `action_by_item` is the type-discrimination source (an item absent from the map is
    an untraced create_post root); round = int(e.time) / int(r.time), fail-closed on a non-integral
    or negative time. `n_rounds` is inferred as max(observed event round, observed refresh round)
    + 1 (mirrors extract_marginals' own inference rule), fail-closed if there is nothing to infer
    it from (no events and no refreshes)."""
    events, refreshes, action_by_item = load_harness_records(db_path, timestamp_col="created_at")

    event_rounds = [_round_of(e.time, kind="event") for e in events]
    refresh_rounds = [_round_of(r.time, kind="refresh") for r in refreshes]
    max_round = max(event_rounds + refresh_rounds, default=-1)
    if max_round < 0:
        raise ValueError(
            "extract_action_profile: no events and no refreshes — cannot infer round count "
            "(fail-closed)")
    n_rounds = max_round + 1

    type_counts = [[0, 0, 0, 0] for _ in range(n_rounds)]
    refresh_counts = [0] * n_rounds
    news_events = []
    authored_corpus = []

    for event, rnd in zip(events, event_rounds):
        action = action_by_item.get(event.item_id, "create_post")
        is_news = event.agent_id == NEWS_USER_AGENT_ID
        if is_news and action != "create_post":
            raise ValueError(
                f"extract_action_profile: news-user event {event.item_id!r} traced as "
                f"{action!r}, not create_post — news events are always create_post rows by "
                f"construction (fail-closed, schema drift)")
        type_counts[rnd][ACTION_TYPES.index(action)] += 1
        if is_news:
            type_counts[rnd][0] -= 1          # news-adjust: remove the exogenous create_post
            news_events.append((rnd, event.content))
        elif action != "repost":
            authored_corpus.append(event.content)

    for rnd in refresh_rounds:
        refresh_counts[rnd] += 1

    return CohortActionProfile(
        window_seed=window_seed,
        per_round_type_counts=tuple(tuple(row) for row in type_counts),
        per_round_refresh_counts=tuple(refresh_counts),
        news_events=tuple(news_events),
        authored_corpus=tuple(authored_corpus),
    )


# --- canonical codec (the run-codec house pattern: causal_probe_records.py's *_to_bytes /
#     *_from_bytes / *_sha256 triple) — sorted keys, compact separators, trailing newline, and a
#     byte-identity re-encode check on reconstruction so a hash chain can never be laundered
#     through JSON-equivalent-but-non-canonical bytes. -----------------------------------------

def profile_to_bytes(profile) -> bytes:
    if type(profile) is not CohortActionProfile:
        raise TypeError("profile must be exactly CohortActionProfile")
    payload = {
        "window_seed": profile.window_seed,
        "per_round_type_counts": [list(row) for row in profile.per_round_type_counts],
        "per_round_refresh_counts": list(profile.per_round_refresh_counts),
        "news_events": [list(row) for row in profile.news_events],
        "authored_corpus": list(profile.authored_corpus),
    }
    return (
        json.dumps(payload, allow_nan=False, ensure_ascii=False, separators=(",", ":"),
                  sort_keys=True)
        + "\n"
    ).encode("utf-8")


def profile_sha256(profile) -> str:
    return hashlib.sha256(profile_to_bytes(profile)).hexdigest()


def profile_from_bytes(data: bytes) -> CohortActionProfile:
    """Rebuild a CohortActionProfile from its canonical bytes, fail-closed. Schema-free (no
    upstream spec identity to check here, unlike the causal-probe records) but the reconstruction
    must reproduce the input byte-for-byte — JSON-equivalent but non-canonical bytes are rejected
    rather than silently normalized."""
    try:
        payload = json.loads(data)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError(f"action profile bytes are not valid JSON: {exc}")
    try:
        profile = CohortActionProfile(
            window_seed=payload["window_seed"],
            per_round_type_counts=tuple(
                tuple(row) for row in payload["per_round_type_counts"]),
            per_round_refresh_counts=tuple(payload["per_round_refresh_counts"]),
            news_events=tuple(tuple(row) for row in payload["news_events"]),
            authored_corpus=tuple(payload["authored_corpus"]),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"action profile bytes have a drifted schema: {exc}")
    if profile_to_bytes(profile) != data:
        raise ValueError("action profile bytes are not canonical (fail-closed)")
    return profile


def archive_window_db_path(window_seed) -> str:
    """The registered-archive trace DB path for one cohort window seed. Delegates entirely to
    `critaudit.experiments.llm_parrot_null` (`DEFAULT_ARCHIVE`, `_WINDOW_DIRS`, and its own
    `_window_db` join) — no new path logic lives here, so the archive layout has exactly one
    owner."""
    from critaudit.experiments.llm_parrot_null import DEFAULT_ARCHIVE, _window_db
    return _window_db(DEFAULT_ARCHIVE, window_seed)
