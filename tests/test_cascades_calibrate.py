"""Gate-D: #3's bin-width knob was to be frozen by SYNTHETIC RECOVERY. On the project's heavy-tail
market regime the recovery does NOT clear — a #3-recoverability FINDING (logged in DECISIONS.md
2026-06-24, threshold NOT relaxed, grid NOT extended, TAU_Q_K left None). This file LOCKS that finding
as a PASSING characterization so it cannot silently drift back to a 'just lower the threshold' fix.
Mechanism: infinite-mean Lomax delays make a cascade temporally scale-free (one tree smears across most
of the horizon; ~92% of events sit inside a foreign tree's span), so trees overlap at any immigrant rate
and timing alone cannot recover them. Lightening the tail restores recoverability — isolating the tail,
not the extractor, as the cause."""
import numpy as np
import pytest
from critaudit.cascades.calibrate import adjusted_rand, recover_tau_q, REGIME
from critaudit.cascades import spec

# A control grid that brackets the (larger) compact-tree recovery scale (~k=50). The FROZEN spec grid
# (max k=5) does NOT bracket it even on a recoverable regime — a separate observation in DECISIONS.md.
_CONTROL_GRID = spec.TAU_Q_GRID + (10.0, 20.0, 50.0, 100.0, 200.0)


def test_adjusted_rand_basics():
    a = np.array([0, 0, 1, 1])
    assert adjusted_rand(a, a) == 1.0                       # identical clustering
    assert adjusted_rand(a, np.array([0, 1, 0, 1])) < 0.5   # orthogonal


@pytest.mark.slow
def test_tau_q_recovery_blocked_on_heavy_tail_and_the_tail_is_the_cause():
    # THE #3-RECOVERABILITY FINDING, locked as a passing characterization. Deterministic seed.
    # (1) Heavy-tail market regime (eps=0.35, infinite-mean Lomax): timing-only recovery does NOT clear.
    heavy = recover_tau_q(np.random.default_rng(20260623), regime=REGIME)        # frozen spec grid
    assert heavy["cleared"] is False
    assert max(heavy["per_k_ari"].values()) < 0.65          # far below RECOVERY_THRESHOLD (measured ~0.43)

    # (2) The cause is the TAIL, not the extractor: a finite-mean tail (eps=2.0, compact trees) recovers
    # cleanly once the grid brackets its scale. Same harness, same generator — only eps changes.
    light = recover_tau_q(np.random.default_rng(20260623), regime=dict(REGIME, eps=2.0), grid=_CONTROL_GRID)
    assert light["cleared"] is True
    assert max(light["per_k_ari"].values()) >= spec.RECOVERY_THRESHOLD   # measured ~0.99

    # (3) The knob stays UNFROZEN — #3 is calibration-blocked on the data regime.
    assert spec.TAU_Q_K is None
    # Guard against the forbidden 'fix': lowering the threshold to force a heavy-tail clear.
    assert max(heavy["per_k_ari"].values()) < spec.RECOVERY_THRESHOLD
