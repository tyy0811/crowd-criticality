"""Sub-inc-1 driver: run the frozen reference operating point through the self-hosted Modal model,
export each run, apply the positive control (fail-closed), and return diagnostics + token counts.
The OASIS run call (run_oasis_minimal) is the integration seam wired to the Modal OpenAI-compatible
endpoint; everything downstream is the pure pipeline (Tasks 2-8)."""
from __future__ import annotations

from critaudit.sim.harness import harness_spec as hs
from critaudit.sim.harness.oasis_adapter import run_oasis_minimal, export_harness_run
from critaudit.sim.harness.positive_control import check_positive_control


def run_reference_cohort(endpoint_url, token, *, timestamp_col):
    """Run the frozen COHORT_SEEDS through the frozen OPERATING_POINT on the given OpenAI-compatible
    endpoint, one seed at a time. Per seed: run_oasis_minimal -> export_harness_run ->
    check_positive_control (which RAISES, fail-closed, on a degenerate/empty reference — the failure
    is a finding, not a return value). Returns list[dict], one per seed: the positive-control
    diagnostics plus {seed, n_events, tokens}. GPU is spent here (the @slow cohort test drives it)."""
    results = []
    for seed in hs.COHORT_SEEDS:
        db_path, token_counts = run_oasis_minimal(
            seed=seed, operating_point=hs.OPERATING_POINT,
            model_id=hs.MODEL_ID, endpoint_url=endpoint_url, token=token)
        run = export_harness_run(db_path, timestamp_col=timestamp_col)
        diag = check_positive_control(run)        # raises (fail-closed) if degenerate
        diag.update(seed=seed, n_events=int(run.times.size), tokens=token_counts)
        results.append(diag)
    return results
