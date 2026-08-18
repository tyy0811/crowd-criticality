# src/critaudit/sim/controls/parrot_v2_spec.py
"""FROZEN surface for OASIS parrot null v2 (Branch-B rev-5 spec, signed off
2026-07-31). Prospective registration: extends, never edits, llm_parrot_spec's
matched-null surface; the v1 do-not-match list BINDS UNCHANGED (branching ratio,
avalanche-size distribution, per-agent emission rate never matched).
A change to any constant here is a SPEC CHANGE, not a tweak."""
import numpy as np
from critaudit.sim.harness import harness_spec as _hs
import critaudit.sim.controls.causal_probe_marker_control as _mctl
from critaudit.experiments.causal_probe_power import (
    POWER_SCHEDULE_SEEDS as _POWER_SCHEDULE_SEEDS,
    RECOVERABILITY_SEEDS as _RECOVERABILITY_SEEDS)

SCHEMA = 1
DESIGN_DOC = "docs/superpowers/specs/2026-07-30-branchb-parrot-null-design.md"
# The signed design is a git-ignored living doc: its pin is THIS literal (owner-
# verified 2026-07-31) plus the Task-0 disk preflight — never a committed file hash.
DESIGN_DOC_SHA256 = "1b8fe8cfa51f935dd8ff6e7fe1710616bee74685301e418f3132bc650c670ac6"

SCHEDULE_SEEDS = tuple(818201 + i for i in range(12))
VIOLATOR_SCHEDULE_SEEDS = (818201, 818202, 818203)   # one per cohort window (round-robin)
WIDTHS = (1, 3, 5)              # shipped endpoints 1, 5 + ratified midpoint 3
MAX_REC_POST_LEN = 5            # driver buffer >= max width (cohort driver value)

V2_NAMESPACE_KEY = 818          # SeedSequence spawn key (818, stream); pinned by test
STREAM_CONTENT = 0
STREAM_TYPE = 1
STREAM_AGENT = 2
STREAM_TARGET = 3
STREAM_REFRESH = 4
STREAM_PLATFORM = 5

CEILING_SECONDS = 4 * 3600
EXPECTED_INVARIANCE_RUNS = 36   # 12 schedules x 3 widths
EXPECTED_VIOLATOR_RUNS = 9      # 3 schedules x 3 widths

REFRESH_EMPTY_OK = "No posts found."   # the ONE tolerated unsuccessful action return

# Every seed registry/range this project has ever reserved. First four entries are
# the LIVE imported registries (order matters for the spec test); the literals
# reserve the diagnostic panels A/B/C, the holdout, the lever-2/Task-0 fixture
# seeds, and the lever-2 shadow ranges.
RESERVED_SEED_RANGES = (
    tuple(_hs.COHORT_SEEDS),
    tuple(_mctl.MARKER_SEEDS),
    tuple(_RECOVERABILITY_SEEDS),
    tuple(_POWER_SCHEDULE_SEEDS),
    tuple(717201 + i for i in range(12)),      # diagnostic panel A
    tuple(727201 + i for i in range(12)),      # diagnostic panel B
    tuple(737201 + i for i in range(12)),      # diagnostic panel C
    tuple(747201 + i for i in range(12)),      # diagnostic holdout
    tuple(424201 + i for i in range(12)),      # lever-2 small-grid reply seeds
    (424242,),                                  # lever-2 SMALL_SEED
    tuple(515201 + i for i in range(12)),      # lever-2 small marker seeds
    tuple(5_000_000_001 + i for i in range(12)),   # shadow reply
    tuple(5_100_000_001 + i for i in range(12)),   # shadow marker
    (5_200_000_001,),                               # shadow gate-A seed
)


def assigned_window(schedule_seed: int) -> int:
    """Round-robin over COHORT_SEEDS ascending (llm_parrot_spec precedent)."""
    i = SCHEDULE_SEEDS.index(int(schedule_seed))
    return _hs.COHORT_SEEDS[i % len(_hs.COHORT_SEEDS)]


def v2_rng(schedule_seed: int, stream: int):
    return np.random.default_rng(np.random.SeedSequence(
        int(schedule_seed), spawn_key=(V2_NAMESPACE_KEY, int(stream))))


def platform_seed(schedule_seed: int) -> int:
    """One platform seed per schedule, REUSED across all widths (spec §3);
    seeds the GLOBAL random module in the fresh replay subprocess."""
    return int(v2_rng(schedule_seed, STREAM_PLATFORM).integers(0, 2**63 - 1))
