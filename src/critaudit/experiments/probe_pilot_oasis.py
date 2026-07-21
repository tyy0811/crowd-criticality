"""Sub-inc-3 OASIS accessibility pilot (T10) — AUTHORIZED by the owner 2026-07-21 on
locator-PASS-alone ("the pilot measures channel accessibility, so the failed n_resp transform is
not relevant to authorization").

SCOPE (owner's constraints, verbatim discipline): enforce the frozen exposure gate
(probe_spec.PILOT_*); treat ALL response values as DESCRIPTIVE — no OASIS-transfer claim, no
regime claim, no H1b claim, no line-189 independence claim, in ANY branch. The pilot asks one
question: is the injection channel ACCESSIBLE on this substrate (markers get served; responses
are readable fail-closed)?

Construction (frozen at the sub-inc-3 freeze, probe_spec §OASIS): one window, SEED_PROBE,
OPERATING_POINT unchanged except the schedule — deterministic injections at rounds (2,4,6,8,10),
markers = NEWS_POOL[0..4] in round order, through the EXISTING model-free manual news channel.
Exposures(m) = # REFRESH trace rows whose served set contains marker m; response = true-link tree
size rooted at m (DB-side BFS over post.original_post_id + comment.post_id — post_reply_tree
semantics on true links, independent of the exporter); per-exposure normalization
(tree_size - 1)/exposures; exposures = 0 -> undefined-inaccessible (NEVER 0). The
finite-memory-horizon and exposure-volume caveats apply to every number below.

NOT in CI: this script costs ~$2 of Modal GPU (the one paid step of sub-inc 3)."""
from __future__ import annotations
import json
import os
import sqlite3

from critaudit.sim.controls import probe_spec as pspec
from critaudit.sim.harness import harness_spec as hs
from critaudit.sim.harness.oasis_adapter import _served_post_ids, export_harness_run

BANKED_PILOT_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "results", "s3_probe", "2026-07-21_pilot_accessibility.json")


def build_probe_schedule(n_rounds=None):
    """The frozen deterministic pilot schedule: NEWS_POOL[k] submitted in round
    PILOT_INJECTION_ROUNDS[k]; every other round None. Pure, no draws."""
    if n_rounds is None:
        n_rounds = hs.OPERATING_POINT["n_rounds"]
    schedule = [None] * int(n_rounds)
    for k, r in zip(pspec.PILOT_MARKER_POOL_INDICES, pspec.PILOT_INJECTION_ROUNDS):
        schedule[r] = hs.NEWS_POOL[k]
    return schedule


def marker_post_ids(db_path, *, news_user_id=None):
    """The news user's posts in post_id order = injection order (fail-closed on a count
    mismatch with the frozen schedule)."""
    if news_user_id is None:
        news_user_id = hs.NEWS_USER_AGENT_ID
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT post_id, content FROM post WHERE user_id=? ORDER BY post_id",
                           (news_user_id,)).fetchall()
    finally:
        con.close()
    expected = [hs.NEWS_POOL[k] for k in pspec.PILOT_MARKER_POOL_INDICES]
    if [c for _, c in rows] != expected:
        raise ValueError(
            f"marker posts in DB do not match the frozen schedule (got {len(rows)}, "
            f"expected {len(expected)} in NEWS_POOL order) — fail-closed")
    return [pid for pid, _ in rows]


def count_exposures(db_path, post_ids):
    """exposures(m) = number of REFRESH trace rows whose served set contains post m."""
    counts = {pid: 0 for pid in post_ids}
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        for (info,) in con.execute("SELECT info FROM trace WHERE action='refresh'"):
            served = set(_served_post_ids(info))
            for pid in post_ids:
                if pid in served:
                    counts[pid] += 1
    finally:
        con.close()
    return counts


def marker_tree_size(db_path, root_post_id):
    """True-link tree size rooted at the marker (root included): BFS over
    post.original_post_id (quotes/reposts) + comment.post_id (comments are leaves) — the
    post_reply_tree semantics on true links, computed DB-side."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        size = 0
        frontier = [root_post_id]
        while frontier:
            size += len(frontier)
            nxt = []
            for pid in frontier:
                size += con.execute("SELECT COUNT(*) FROM comment WHERE post_id=?",
                                    (pid,)).fetchone()[0]
                nxt.extend(p for (p,) in con.execute(
                    "SELECT post_id FROM post WHERE original_post_id=?", (pid,)))
            frontier = nxt
    finally:
        con.close()
    return size


def analyze_pilot(db_path):
    """The frozen accessibility gate + descriptive response record. Returns the banked record;
    RAISES only on structural failure (export/schedule mismatch); an accessibility FAIL is a
    first-class recorded status, not an exception."""
    run = export_harness_run(db_path, timestamp_col="created_at")   # fail-closed export clause
    pids = marker_post_ids(db_path)
    exposures = count_exposures(db_path, pids)
    markers = []
    for k, pid in enumerate(pids):
        tree = marker_tree_size(db_path, pid)
        exp = exposures[pid]
        markers.append({
            "marker_index": k,
            "post_id": pid,
            "round_submitted": pspec.PILOT_INJECTION_ROUNDS[k],
            "exposures": exp,
            "tree_size": tree,
            # exposures = 0 -> undefined-inaccessible, NEVER 0 (fail-closed semantics):
            "response_per_exposure": ((tree - 1) / exp if exp > 0 else None),
        })
    n_exposed = sum(1 for m in markers if m["exposures"] >= 1)
    total_exposures = sum(m["exposures"] for m in markers)
    gate_pass = (n_exposed >= pspec.PILOT_MIN_EXPOSED_MARKERS
                 and total_exposures >= pspec.PILOT_MIN_TOTAL_EXPOSURES)
    return {
        "artifact": "pilot_accessibility",
        "design": pspec.DESIGN_DOC,
        "design_sha256": pspec.DESIGN_DOC_SHA256,
        "authorization": "owner 2026-07-21: locator-PASS-alone; responses DESCRIPTIVE only — "
                         "no OASIS-transfer, regime, H1b, or line-189 independence claim",
        "status": "ACCESSIBLE" if gate_pass else "INACCESSIBLE",
        "n_markers_exposed": n_exposed,
        "total_marker_exposures": total_exposures,
        "thresholds": {"min_exposed_markers": pspec.PILOT_MIN_EXPOSED_MARKERS,
                       "min_total_exposures": pspec.PILOT_MIN_TOTAL_EXPOSURES},
        "markers": markers,
        "n_events_exported": int(run.times.size),
        "caveats": "finite-memory-horizon + exposure-volume (inherited from the harness); all "
                   "response values are DESCRIPTIVE",
    }


def bank_pilot(record, out_path=BANKED_PILOT_JSON):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(record, f, sort_keys=True, indent=1, allow_nan=False)
        f.write("\n")
