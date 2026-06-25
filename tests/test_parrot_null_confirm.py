import numpy as np
import pytest
from critaudit.experiments.parrot_null import run_parrot_null
from critaudit.sim.controls import parrot_spec as ps

pytestmark = pytest.mark.slow   # full substrate + CSN bootstrap + gate ll_grid -> minutes; excluded from CI fast path


@pytest.fixture(scope="module")
def res():
    return run_parrot_null(seed=ps.SEED)   # full frozen substrate


def test_positive_control_null_is_real(res):
    # the null is genuinely instantiated: no belief-coupled success, no structural edge
    assert res.tripwire_ok is True              # parrot.successes == 0
    assert res.struct_ok is True
    assert res.parrot.n_struct == 0.0           # n_gen and n_struct both 0 -> licenses reading a surviving τ as spurious


def test_artifact_test_null_confirmation(res):
    # LOAD-BEARING null-confirmation: the collapsed null admits NO power law (every avalanche is size 1,
    # the size distribution a delta at 1). The dangerous failure mode — a null that spuriously fires τ —
    # is exactly what this rules out: the parrot's τ is undefined and .passes is False.
    assert res.parrot.tau_passes is ps.TAU_NULL_PASSES          # False
    assert np.isnan(res.parrot.tau)

    # Coupled-side SEPARATION rides the THEORY-ANCHORED τ-band (mean-field critical 3/2), the criterion
    # increment-3 ACTUALLY anchored: test_shakedown_discrim::test_crit_tau_corroborates_criticality asserts
    # ONLY |τ - TAU_TARGET| <= TAU_TOL on the CRIT plant. The coupled CRIT exponent is recovered essentially
    # exactly; the null has no exponent at all — that IS the artifact-test separation (structure -> a
    # critical exponent; no structure -> no exponent). (Freeze-correction over the design doc §7 over-claim;
    # see the 2026-06-25 DECISIONS entry.)
    assert np.isfinite(res.coupled.tau)
    assert abs(res.coupled.tau - ps.TAU_TARGET) <= ps.TAU_TOL    # coupled CRIT τ ≈ 3/2 (incr-3 anchor)

    # The strict CSN .passes / p_boot are RECORDED-NOT-ASSERTED here, exactly as increment-3 treats p_boot
    # (a budget knob, never a frozen threshold — test_shakedown_discrim lines 10-14). The full-shape Clauset
    # bootstrap REJECTS the coupled CRIT (p_boot -> 0, .passes False) DESPITE the near-perfect exponent,
    # because a critical-branching avalanche distribution carries a finite-size cutoff (max size ~ N) that is
    # a genuine departure from a PURE power law. SCOPE: this means p_boot-strict is the wrong instrument for
    # "is the exponent critical" (the τ-band is the right one) — it is NOT evidence the gate is unreliable for
    # "is this a clean power law over its fitted range." We assert only well-formedness, never a value.
    for c in (res.coupled, res.parrot):
        assert isinstance(c.tau_passes, bool)
    assert np.isfinite(res.coupled.p_boot) and np.isnan(res.parrot.p_boot)


def test_emission_time_analog_column(res):
    # n_emit: 0 at the null; crosses toward 1 at coupled CRIT (construction soundness; full crossing
    # over LOW/CRIT/HIGH is established by increment-3's test_anchors.py — cited, not re-run here)
    assert res.parrot.n_emit == ps.N_EMIT_NULL                  # 0.0
    assert res.coupled.n_emit >= ps.N_EMIT_REF_MIN              # ~1.3 in incr-3


def test_temporal_clustering_column(res):
    # parrot reads the Poisson baseline (B≈0, F≈1 across scales); coupled is clustered (separation)
    assert res.parrot.burstiness <= ps.BURST_NULL_HI
    assert np.all(res.parrot.fano >= ps.FANO_NULL_LO)
    assert np.all(res.parrot.fano <= ps.FANO_NULL_HI)
    assert res.coupled.burstiness > res.parrot.burstiness
    assert np.nanmax(res.coupled.fano) > np.nanmax(res.parrot.fano)


def test_blind_reference_gate_logged_not_asserted(res):
    # n̂ is a BLIND-REFERENCE column: finite and recorded for both, NO discrimination asserted
    for c in (res.coupled, res.parrot):
        assert np.isfinite(c.gate_peak) and np.isfinite(c.gate_migrated)
        assert isinstance(c.gate_identified, bool)


def test_determinism_regression(res):
    again = run_parrot_null(seed=ps.SEED)
    assert again.parrot.n_struct == res.parrot.n_struct == 0.0
    assert again.coupled.n_emit == res.coupled.n_emit
    assert np.array_equal(again.parrot.fano, res.parrot.fano)
