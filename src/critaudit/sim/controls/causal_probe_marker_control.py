"""Disjoint recursive marker control for `chi_resp` on the installed OASIS platform.

Marker cascades are realized as native quote chains driven by a scripted non-LLM
policy: every node authored in round r gets exactly `opportunities_per_parent`
response opportunities when it first becomes readable in round r+1, each firing
independently with the frozen `response_probability = plant_r /
opportunities_per_parent`, so the expected one-generation reproduction is exactly
`plant_r`. The installed platform resolves a quote-of-a-quote's
`original_post_id` to the ROOT post, so cascades are star-shaped in the database;
per-root tree SIZES — the only quantity `chi_resp = CV^2(S)` consumes — are
unaffected, and sizes are measured through the production export
(`export_harness_run` -> `post_reply_tree` link semantics).

Disjointness from the one-generation `R_reply` control is structural: a dedicated
seed-stream namespace (`control:marker`), marker-prefixed manifest IDs, and a
registered round allocation starting at `MARKER_ROUND_OFFSET = 2` (the `R_reply`
control layout occupies rounds 0-1), so the two controls can never share
run/frame/seed-stream/root/round/event/pair/assignment identifiers.

The registry frozen here (`MARKER_SEEDS`, `PLANT_R_GRID`, 512/4/8) carries the
result-blind values stated verbatim in the ratified implementation plan; Task 7
banks them alongside the power surface and applies the cross-registry
disjointness firewall.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

__all__ = (
    "MARKER_SEED_STREAM",
    "MARKER_SEEDS",
    "MARKER_ROOT_COUNT",
    "MARKER_OPPORTUNITIES_PER_PARENT",
    "MARKER_ROUNDS",
    "MARKER_ROUND_OFFSET",
    "MARKER_RNG_STREAM_RESPONSES",
    "PLANT_R_GRID",
    "MarkerManifest",
    "MarkerControlResult",
    "MarkerGridCell",
    "ChiPeak",
    "aggregate_marker_cell",
    "compute_chi_resp",
    "locate_chi_peak",
    "require_disjoint_manifests",
    "require_disjoint_seed_sets",
    "run_recursive_marker_control",
)

MARKER_SEED_STREAM = "control:marker"
_MARKER_SEED_STREAM_KEYS = {MARKER_SEED_STREAM: 912}
MARKER_RNG_STREAM_RESPONSES = 921

MARKER_SEEDS = (
    2026072401, 2026072402, 2026072403, 2026072404,
    2026072405, 2026072406, 2026072407, 2026072408,
    2026072409, 2026072410, 2026072411, 2026072412,
)
MARKER_ROOT_COUNT = 512
MARKER_OPPORTUNITIES_PER_PARENT = 4
MARKER_ROUNDS = 8
MARKER_ROUND_OFFSET = 2

PLANT_R_GRID = (0.60, 0.92, 0.97, 1.03, 1.08, 1.30)


@dataclass(frozen=True)
class MarkerManifest:
    run_id: str
    frame_id: str
    seed_stream_id: str
    raw_seed: int
    plant_r: float
    response_probability: float
    root_count: int
    opportunities_per_parent: int
    rounds: int
    root_ids: tuple[str, ...]
    round_ids: tuple[int, ...]
    event_ids: tuple[str, ...]
    pair_ids: tuple[str, ...]
    assignment_ids: tuple[str, ...]
    support_per_root: tuple[int, ...]


@dataclass(frozen=True)
class MarkerControlResult:
    manifest: MarkerManifest
    tree_sizes: tuple[int, ...]
    chi_resp: float


@dataclass(frozen=True)
class MarkerGridCell:
    plant_r: float
    seed_results: tuple[MarkerControlResult, ...]
    pooled_tree_sizes: tuple[int, ...]
    aggregated_chi_resp: float


@dataclass(frozen=True)
class ChiPeak:
    argmax_plant_r: float
    neighbor_low: float
    neighbor_high: float
    prominence: float
    seed_argmax_consistency_count: int
    seed_count: int


def _marker_response_rng(seed_stream_id, seed):
    key = _MARKER_SEED_STREAM_KEYS.get(seed_stream_id)
    if key is None:
        raise ValueError(f"unregistered marker seed stream {seed_stream_id!r} (fail-closed)")
    return np.random.default_rng(
        np.random.SeedSequence(int(seed), spawn_key=(key, MARKER_RNG_STREAM_RESPONSES))
    )


def compute_chi_resp(tree_sizes) -> float:
    """chi_resp = CV^2(S) = population_variance(sizes) / mean(sizes)^2."""
    sizes = tuple(tree_sizes)
    if not sizes:
        raise ValueError("chi_resp needs a non-empty tree-size tuple")
    values = np.asarray(sizes, dtype=float)
    mean = float(values.mean())
    if mean == 0.0:
        raise ValueError("chi_resp is undefined for a zero mean tree size")
    return float(values.var() / (mean * mean))


def _validate_marker_manifest(manifest, position, plant_r):
    if type(manifest) is not MarkerManifest:
        raise ValueError(f"seed_results[{position}] does not carry a MarkerManifest")
    if manifest.seed_stream_id != MARKER_SEED_STREAM:
        raise ValueError(
            f"seed_results[{position}] is relabeled onto stream "
            f"{manifest.seed_stream_id!r} (fail-closed)")
    if manifest.raw_seed != MARKER_SEEDS[position]:
        raise ValueError(
            f"seed_results[{position}] raw seed {manifest.raw_seed} does not equal "
            f"MARKER_SEEDS[{position}] = {MARKER_SEEDS[position]}")
    if manifest.plant_r != plant_r:
        raise ValueError(
            f"seed_results[{position}] plant_r {manifest.plant_r} does not equal "
            f"the cell plant_r {plant_r}")
    if manifest.root_count != MARKER_ROOT_COUNT:
        raise ValueError(f"seed_results[{position}] root_count is not frozen 512")
    if manifest.opportunities_per_parent != MARKER_OPPORTUNITIES_PER_PARENT:
        raise ValueError(
            f"seed_results[{position}] opportunities_per_parent is not frozen 4")
    if manifest.rounds != MARKER_ROUNDS:
        raise ValueError(f"seed_results[{position}] rounds is not frozen 8")
    expected_q = plant_r / MARKER_OPPORTUNITIES_PER_PARENT
    if manifest.response_probability != expected_q:
        raise ValueError(
            f"seed_results[{position}] response_probability "
            f"{manifest.response_probability} != plant_r/4 = {expected_q}")
    if len(manifest.root_ids) != MARKER_ROOT_COUNT:
        raise ValueError(f"seed_results[{position}] root_ids length drifted")
    if manifest.support_per_root != (
        MARKER_OPPORTUNITIES_PER_PARENT,
    ) * MARKER_ROOT_COUNT:
        raise ValueError(
            f"seed_results[{position}] support_per_root is not the equal "
            f"registered support (fail-closed)")


def aggregate_marker_cell(plant_r, seed_results) -> MarkerGridCell:
    """Pool one plant cell's 12 seed results with equal root weight.

    The aggregated statistic is CV^2 over the CONCATENATED 6,144 tree sizes;
    averaging or taking a median of per-seed CV^2 values is forbidden and
    structurally impossible through this function."""
    results = tuple(seed_results)
    if len(results) != len(MARKER_SEEDS):
        raise ValueError(
            f"a marker cell requires exactly {len(MARKER_SEEDS)} seed results, "
            f"got {len(results)}")
    pooled = []
    for position, result in enumerate(results):
        if type(result) is not MarkerControlResult:
            raise ValueError(f"seed_results[{position}] is not a MarkerControlResult")
        _validate_marker_manifest(result.manifest, position, plant_r)
        if type(result.tree_sizes) is not tuple or (
            len(result.tree_sizes) != MARKER_ROOT_COUNT
        ):
            raise ValueError(
                f"seed_results[{position}] tree_sizes must carry exactly one size "
                f"per registered root")
        if result.chi_resp != compute_chi_resp(result.tree_sizes):
            raise ValueError(
                f"seed_results[{position}] chi_resp does not reproduce from its "
                f"tree sizes (fail-closed)")
        pooled.extend(result.tree_sizes)
    pooled = tuple(pooled)
    return MarkerGridCell(
        plant_r=plant_r,
        seed_results=results,
        pooled_tree_sizes=pooled,
        aggregated_chi_resp=compute_chi_resp(pooled),
    )


def locate_chi_peak(cells) -> ChiPeak:
    """Interior unique aggregated maximum over the six registered plant cells,
    with per-seed argmax consistency required at the same cell."""
    cells = tuple(cells)
    if len(cells) != len(PLANT_R_GRID):
        raise ValueError(
            f"locate_chi_peak consumes exactly {len(PLANT_R_GRID)} cells")
    for index, cell in enumerate(cells):
        if type(cell) is not MarkerGridCell:
            raise ValueError(f"cells[{index}] is not a MarkerGridCell")
        if cell.plant_r != PLANT_R_GRID[index]:
            raise ValueError(
                f"cells[{index}] plant_r {cell.plant_r} is out of PLANT_R_GRID "
                f"order (expected {PLANT_R_GRID[index]})")

    aggregated = [cell.aggregated_chi_resp for cell in cells]
    peak_value = max(aggregated)
    argmax_positions = [i for i, value in enumerate(aggregated) if value == peak_value]
    if len(argmax_positions) != 1:
        raise ValueError("aggregated chi_resp maximum is not unique (fail-closed)")
    argmax = argmax_positions[0]
    if argmax == 0 or argmax == len(cells) - 1:
        raise ValueError(
            "aggregated chi_resp maximum sits on the grid boundary (fail-closed)")
    prominence = peak_value - max(
        value for i, value in enumerate(aggregated) if i != argmax)

    seed_count = len(MARKER_SEEDS)
    consistent = 0
    for position in range(seed_count):
        seed_chis = [cell.seed_results[position].chi_resp for cell in cells]
        seed_peak = max(seed_chis)
        seed_argmaxes = [i for i, value in enumerate(seed_chis) if value == seed_peak]
        if seed_argmaxes == [argmax]:
            consistent += 1
    if consistent != seed_count:
        raise ValueError(
            f"seed argmax consistency failed: {consistent}/{seed_count} seed "
            f"positions peak at the aggregated argmax (fail-closed)")
    return ChiPeak(
        argmax_plant_r=PLANT_R_GRID[argmax],
        neighbor_low=PLANT_R_GRID[argmax - 1],
        neighbor_high=PLANT_R_GRID[argmax + 1],
        prominence=prominence,
        seed_argmax_consistency_count=consistent,
        seed_count=seed_count,
    )


def require_disjoint_manifests(reply_manifest, marker_manifest):
    """Independence firewall between the `R_reply` (ProbeManifest) and `chi_resp`
    (MarkerManifest) cohorts: shared identifiers in ANY field fail closed."""
    for field in ("run_id", "frame_id", "seed_stream_id", "raw_seed"):
        if getattr(reply_manifest, field) == getattr(marker_manifest, field):
            raise ValueError(
                f"reply and marker manifests share {field} "
                f"({getattr(reply_manifest, field)!r}) — cohorts are not disjoint")
    for field in ("root_ids", "round_ids", "event_ids", "pair_ids", "assignment_ids"):
        overlap = set(getattr(reply_manifest, field)) & set(
            getattr(marker_manifest, field))
        if overlap:
            raise ValueError(
                f"reply and marker manifests overlap in {field}: "
                f"{sorted(overlap)[:3]!r} — cohorts are not disjoint")


def require_disjoint_seed_sets(*seed_sets):
    """Generic pairwise-disjointness guard for frozen seed registries."""
    for i in range(len(seed_sets)):
        for j in range(i + 1, len(seed_sets)):
            overlap = set(seed_sets[i]) & set(seed_sets[j])
            if overlap:
                raise ValueError(
                    f"seed sets {i} and {j} overlap on {sorted(overlap)!r} "
                    f"(fail-closed)")


async def _drive_recursive_marker_control(root_count, opportunities_per_parent,
                                          plant_r, rounds, run_id, frame_id,
                                          seed_stream_id, seed, database_path,
                                          response_probability):
    from oasis import ActionType, AgentGraph, SocialAgent, make
    from oasis.social_platform.channel import Channel
    from oasis.social_platform.platform import Platform
    from oasis.social_platform.typing import RecsysType

    from critaudit.cascades.extract import post_reply_tree
    from critaudit.sim.harness import harness_spec as hs
    from critaudit.sim.harness.oasis_adapter import (
        _make_news_sentinel_model,
        _new_user_info,
        export_harness_run,
    )

    rng = _marker_response_rng(seed_stream_id, seed)

    sentinel = _make_news_sentinel_model(
        model_id="marker-sentinel", endpoint_url="http://sentinel.invalid/v1",
        token="marker", max_tokens=64, temperature=0.0, timeout=5,
        context_budget=1024)

    platform = Platform(
        db_path=database_path,
        channel=Channel(),
        recsys_type=RecsysType(hs.RECSYS_TYPE),
        refresh_rec_post_count=3,
        max_rec_post_len=5,
        following_post_count=hs.FOLLOWING_POST_COUNT,
    )

    graph = AgentGraph()
    available = [ActionType(name) for name in
                 ("create_post", "create_comment", "repost", "quote_post", "do_nothing")]
    agent_names = {0: "marker_root_author"}
    for slot in range(opportunities_per_parent):
        agent_names[1 + slot] = f"marker_recipient_{slot}"
    for agent_id in sorted(agent_names):
        graph.add_agent(SocialAgent(
            agent_id=agent_id,
            user_info=_new_user_info(name=agent_names[agent_id], bio="marker fixture",
                                     user_profile="marker fixture"),
            model=sentinel, available_actions=available))

    env = make(agent_graph=graph, platform=platform, database_path=database_path)
    await env.reset()
    event_ids = []
    pair_ids = []
    assignment_ids = []
    try:
        for _ in range(MARKER_ROUND_OFFSET):
            await env.step({})   # burn the disjoint-round offset

        roots = []
        for k in range(root_count):
            result = await graph.get_agent(0).env.action.create_post(
                f"marker root {k + 1}")
            if not (result.get("success") is True and result.get("post_id") == k + 1):
                raise RuntimeError(f"marker root creation drifted: {result!r}")
            roots.append(k + 1)
            event_ids.append(f"marker:post:{k + 1}")

        # generation g nodes (authored in round OFFSET+g-1) get their single
        # opportunity block when first readable in round OFFSET+g
        previous_generation = list(roots)
        for generation in range(1, rounds):
            await env.step({})
            next_generation = []
            for node_db_id in previous_generation:
                for slot in range(opportunities_per_parent):
                    pair_ids.append(f"marker-pair:post:{node_db_id}:{slot}")
                    if float(rng.random()) >= response_probability:
                        continue
                    result = await graph.get_agent(1 + slot).env.action.quote_post(
                        node_db_id, f"marker reply to {node_db_id}")
                    if not (result.get("success") is True and "post_id" in result):
                        raise RuntimeError(f"marker reply failed: {result!r}")
                    child_db_id = int(result["post_id"])
                    next_generation.append(child_db_id)
                    event_ids.append(f"marker:post:{child_db_id}")
                    assignment_ids.append(f"marker-assignment:post:{child_db_id}")
            previous_generation = next_generation
    finally:
        await env.close()

    run = export_harness_run(database_path, timestamp_col="created_at")
    root_indices = np.flatnonzero(run.parent_idx < 0)
    if len(root_indices) != root_count:
        raise RuntimeError(
            f"marker export found {len(root_indices)} roots, expected {root_count}")
    post_reply_tree(run.times, run.root_id, run.parent_idx)  # production link check
    tree_sizes = tuple(
        int((run.root_id == int(index)).sum()) for index in root_indices)

    manifest = MarkerManifest(
        run_id=run_id,
        frame_id=frame_id,
        seed_stream_id=seed_stream_id,
        raw_seed=int(seed),
        plant_r=float(plant_r),
        response_probability=response_probability,
        root_count=int(root_count),
        opportunities_per_parent=int(opportunities_per_parent),
        rounds=int(rounds),
        root_ids=tuple(f"marker:post:{k}" for k in roots),
        round_ids=tuple(range(MARKER_ROUND_OFFSET, MARKER_ROUND_OFFSET + rounds)),
        event_ids=tuple(event_ids),
        pair_ids=tuple(pair_ids),
        assignment_ids=tuple(assignment_ids),
        support_per_root=(int(opportunities_per_parent),) * int(root_count),
    )
    return MarkerControlResult(
        manifest=manifest,
        tree_sizes=tree_sizes,
        chi_resp=compute_chi_resp(tree_sizes),
    )


def run_recursive_marker_control(
    root_count: int,
    opportunities_per_parent: int,
    plant_r: float,
    rounds: int,
    run_id: str,
    frame_id: str,
    seed_stream_id: str,
    seed: int,
    database_path: str,
) -> MarkerControlResult:
    """Installed-OASIS recursive marker control (scripted, non-LLM, fail-closed
    sentinel model). All roots are planted in the first marker round, so every
    root has the identical complete horizon and equal registered support; a
    layout that would plant late (incomplete-horizon) roots is not expressible
    here."""
    import asyncio

    root_count = int(root_count)
    opportunities_per_parent = int(opportunities_per_parent)
    rounds = int(rounds)
    if root_count < 1 or opportunities_per_parent < 1 or rounds < 2:
        raise ValueError("marker control needs >= 1 root, >= 1 opportunity, >= 2 rounds")
    response_probability = float(plant_r) / opportunities_per_parent
    if not 0.0 <= response_probability <= 1.0 or not math.isfinite(response_probability):
        raise ValueError(
            f"response_probability = plant_r / opportunities_per_parent must lie "
            f"in [0, 1], got {response_probability}")
    _marker_response_rng(seed_stream_id, seed)  # reject unregistered streams up front

    return asyncio.run(_drive_recursive_marker_control(
        root_count, opportunities_per_parent, plant_r, rounds, run_id, frame_id,
        seed_stream_id, seed, database_path, response_probability))
