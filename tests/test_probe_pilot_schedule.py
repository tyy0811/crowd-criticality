"""Fast tests for the sub-inc-3 pilot machinery (T10): the frozen deterministic schedule, the
resolve_schedule default-path equivalence (the keyword-only extension must be byte-equivalent to
pre-extension behavior when schedule=None), and the exposure/tree accounting verified against the
known synthetic DB (the metric-sanity pre-flight analog). The paid pilot run itself is NOT in CI."""
import pytest

from critaudit.experiments.probe_pilot_oasis import (
    build_probe_schedule, count_exposures, marker_post_ids, marker_tree_size)
from critaudit.sim.controls import probe_spec as pspec
from critaudit.sim.harness import harness_spec as hs
from critaudit.sim.harness.oasis_adapter import build_news_schedule, resolve_schedule
# Sibling test module imported TOP-LEVEL (no `tests.` prefix): pytest's prepend import-mode puts
# tests/ itself on sys.path in every invocation, whereas the `tests.` package form only resolved
# locally by the accident of `python -m pytest` from the repo root (CI runs bare `pytest` — the
# PR #11 collection failure, 2026-07-21).
from test_harness_export import _build_synthetic_oasis_db


def test_probe_schedule_deterministic_and_frozen():
    s1, s2 = build_probe_schedule(), build_probe_schedule()
    assert s1 == s2
    assert len(s1) == hs.OPERATING_POINT["n_rounds"]
    injected = {r: c for r, c in enumerate(s1) if c is not None}
    assert tuple(injected) == pspec.PILOT_INJECTION_ROUNDS
    assert list(injected.values()) == [hs.NEWS_POOL[k] for k in pspec.PILOT_MARKER_POOL_INDICES]
    assert len(set(injected.values())) == 5                  # distinct markers -> unambiguous


def test_resolve_schedule_default_path_equivalence():
    # schedule=None must reproduce the pre-extension behavior EXACTLY (build_news_schedule on
    # the same seed/operating point) — the tripwire that the extension cannot perturb sub-inc-1
    # semantics.
    op = hs.OPERATING_POINT
    assert resolve_schedule(20260627, op, None) == build_news_schedule(
        20260627, n_rounds=op["n_rounds"], news_rate=op["news_rate"])


def test_resolve_schedule_explicit_passthrough_and_fail_closed():
    op = hs.OPERATING_POINT
    sched = build_probe_schedule()
    assert resolve_schedule(1, op, sched) == sched           # verbatim passthrough
    with pytest.raises(ValueError, match="length"):
        resolve_schedule(1, op, sched[:-1])
    bad = list(sched)
    bad[0] = 123
    with pytest.raises(ValueError, match="neither None nor str"):
        resolve_schedule(1, op, bad)


def test_exposure_and_tree_accounting_on_known_db(tmp_path):
    # Metric sanity on the KNOWN synthetic DB: refresh rowid 3 served posts {1, 2}; trees are
    # post1<-{comment1, comment2, repost4} (size 4), post2<-quote3 (size 2), lone post5 (size 1).
    db = str(tmp_path / "oasis.db")
    _build_synthetic_oasis_db(db)
    exp = count_exposures(db, [1, 2, 5])
    assert exp == {1: 1, 2: 1, 5: 0}
    assert marker_tree_size(db, 1) == 4
    assert marker_tree_size(db, 2) == 2
    assert marker_tree_size(db, 5) == 1
    # marker_post_ids fail-closed: the synthetic DB has no news-user markers.
    with pytest.raises(ValueError, match="fail-closed"):
        marker_post_ids(db)
