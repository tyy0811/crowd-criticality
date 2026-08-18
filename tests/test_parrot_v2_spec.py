# tests/test_parrot_v2_spec.py
import numpy as np


def test_frozen_surface_verbatim():
    import critaudit.sim.controls.parrot_v2_spec as s
    assert s.SCHEMA == 1
    assert s.SCHEDULE_SEEDS == tuple(818201 + i for i in range(12))
    assert s.VIOLATOR_SCHEDULE_SEEDS == (818201, 818202, 818203)
    assert s.WIDTHS == (1, 3, 5)
    assert s.V2_NAMESPACE_KEY == 818
    assert (s.STREAM_CONTENT, s.STREAM_TYPE, s.STREAM_AGENT, s.STREAM_TARGET,
            s.STREAM_REFRESH, s.STREAM_PLATFORM) == (0, 1, 2, 3, 4, 5)
    assert s.MAX_REC_POST_LEN == 5
    assert s.CEILING_SECONDS == 4 * 3600
    assert s.EXPECTED_INVARIANCE_RUNS == 36 and s.EXPECTED_VIOLATOR_RUNS == 9
    assert s.REFRESH_EMPTY_OK == "No posts found."
    # the signed design's pin lives HERE as a literal (the doc itself is
    # git-ignored — a clean clone cannot hash it; Task-0 preflight checks disk)
    assert s.DESIGN_DOC_SHA256 == (
        "1b8fe8cfa51f935dd8ff6e7fe1710616bee74685301e418f3132bc650c670ac6")


def test_seed_disjointness_imported_and_literal_registries():
    import critaudit.sim.controls.parrot_v2_spec as s
    from critaudit.sim.harness import harness_spec as hs
    import critaudit.sim.controls.causal_probe_marker_control as mctl
    from critaudit.experiments.causal_probe_power import (
        POWER_SCHEDULE_SEEDS, RECOVERABILITY_SEEDS)
    live = set(hs.COHORT_SEEDS) | set(mctl.MARKER_SEEDS) | \
        set(RECOVERABILITY_SEEDS) | set(POWER_SCHEDULE_SEEDS)
    assert live == set().union(*(r for r in s.RESERVED_SEED_RANGES[:4]))
    # every reserved range (imported AND literal) is disjoint from v2 seeds
    for rng in s.RESERVED_SEED_RANGES:
        assert not (set(s.SCHEDULE_SEEDS) & set(rng))
    # the literal reservations cover the diagnostic panels, holdout, fixture,
    # and shadow ranges exactly
    flat = set().union(*(set(r) for r in s.RESERVED_SEED_RANGES))
    for probe in (2026072201, 2026072101, 2026072401, 20260627,   # registries
                  717201, 727212, 737205, 747201,                  # panels+holdout
                  424201, 424242, 515201, 515212,                  # fixture seeds
                  5_000_000_001, 5_100_000_012, 5_200_000_001):    # shadow
        assert probe in flat


def test_spawn_key_structure_pinned():
    """v2_rng(seed, stream) IS SeedSequence(seed, spawn_key=(818, stream)) —
    reconstructed independently here so the structure cannot drift silently."""
    import critaudit.sim.controls.parrot_v2_spec as s
    a = s.v2_rng(818201, s.STREAM_TARGET).integers(0, 2**32, 8)
    b = np.random.default_rng(np.random.SeedSequence(
        818201, spawn_key=(818, 3))).integers(0, 2**32, 8)
    assert list(a) == list(b)
    ps = s.platform_seed(818201)
    ps2 = int(np.random.default_rng(np.random.SeedSequence(
        818201, spawn_key=(818, 5))).integers(0, 2**63 - 1))
    assert ps == ps2


def test_window_assignment_round_robin():
    import critaudit.sim.controls.parrot_v2_spec as s
    from critaudit.sim.harness import harness_spec as hs
    got = [s.assigned_window(seed) for seed in s.SCHEDULE_SEEDS[:4]]
    assert got == [hs.COHORT_SEEDS[0], hs.COHORT_SEEDS[1],
                   hs.COHORT_SEEDS[2], hs.COHORT_SEEDS[0]]
    assert [s.assigned_window(v) for v in s.VIOLATOR_SCHEDULE_SEEDS] == list(hs.COHORT_SEEDS)
