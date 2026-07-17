"""Cohort marginal extraction (sub-inc-2 design 2026-07-17 §7) — the ONLY surface through which
cohort data reaches the matched generator.

CohortMarginals is a WHITELISTED two-field dataclass (structural firewall, design §8): the
aggregate per-round emission counts and the authored-text pool. Deliberately nothing else — no
parent structure, no tree statistic, no timing beyond round granularity has a field to ride in on.
tests/test_llm_parrot_firewall.py pins the field set."""
from __future__ import annotations
from dataclasses import dataclass, fields

import numpy as np


@dataclass(frozen=True)
class CohortMarginals:
    """The matched marginals of ONE registered cohort window. per_round_counts[r] = number of
    emitted events with round-granular created_at == r (news immigrants included — they are part
    of the exported stream being matched); authored_texts = the full authored-content pool in
    stream order (repost '' entries included — they are part of the marginal)."""
    per_round_counts: tuple
    authored_texts: tuple


# The whitelist the firewall test pins — change requires a spec change, loudly.
COHORT_MARGINALS_FIELDS = ("per_round_counts", "authored_texts")
assert tuple(f.name for f in fields(CohortMarginals)) == COHORT_MARGINALS_FIELDS


def round_indices(times):
    """Round index per event of a ROUND-GRANULAR stream — the ONE home of the validation
    (fail-closed on empty, non-integral, or negative times), shared by extract_marginals and the
    experiments driver so the calibration streams and the matched per-round profile can never be
    computed under divergent round rules (review consolidation 2026-07-17)."""
    times = np.asarray(times, dtype=float)
    if times.size == 0:
        raise ValueError("round_indices: empty stream (fail-closed)")
    rounds = np.floor(times).astype(np.int64)
    if not np.all(times == rounds):
        raise ValueError("round_indices: non-integral event times — not a round-granular "
                         "stream; per-round semantics undefined (fail-closed)")
    if rounds.min() < 0:
        raise ValueError("round_indices: negative round index")
    return rounds


def extract_marginals(run):
    """HarnessRun -> CohortMarginals. FAIL-CLOSED via round_indices (the exported cohort clock is
    round-granular — created_at = integer round, verified on all 3 archived DBs). n_rounds is
    inferred as max(round)+1 from the observed stream (every registered window has all 20 rounds
    active; a trailing silent round would be invisible here — disclosed)."""
    rounds = round_indices(run.times)
    counts = np.bincount(rounds, minlength=int(rounds.max()) + 1)
    if len(run.content) != rounds.size:
        raise ValueError("extract_marginals: content misaligned with times")
    return CohortMarginals(per_round_counts=tuple(int(c) for c in counts),
                           authored_texts=tuple(run.content))
