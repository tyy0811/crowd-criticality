from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    path = ROOT / relative_path
    assert path.exists(), f"required project-status document is missing: {relative_path}"
    return path.read_text(encoding="utf-8")


def test_readme_names_the_current_reconciliation_checkpoint():
    readme = _read("README.md")

    assert "Current checkpoint (2026-07-22)" in readme
    assert "Stage 2 sub-increment 3" in readme


def test_living_plan_records_each_reconciled_stage_state():
    plan = _read("IMPLEMENTATION_PLAN.md")

    assert "**Version:** v0.4" in plan
    assert "| Stage 0 | Partial |" in plan
    assert "| Stage 1 | Fallback complete |" in plan
    assert "| Stage 2 | Partial and pre-sweep blocked |" in plan
    assert "| Stage 3 | Not started and closed |" in plan
    assert "| Stage 4 | Foundation only |" in plan


def test_global_preregistration_remains_an_unfrozen_draft():
    preregistration = _read("PRE_REGISTRATION.md")

    assert "Global status: DRAFT — never frozen or registered" in preregistration
    assert "cannot be applied retroactively" in preregistration


def test_plan_does_not_authorize_the_sweep_or_stage3():
    plan = _read("IMPLEMENTATION_PLAN.md")

    assert "The original three-way Stage 2 sweep is not authorized" in plan
    assert "Stage 3 remains closed" in plan
    assert "No paid or GPU-backed measurement is authorized by this reconciliation" in plan


def test_plan_records_the_conditional_causal_probe_ratification():
    plan = _read("IMPLEMENTATION_PLAN.md")
    design = _read("results/s3_probe/2026-07-22_oasis_causal_probe_design_review.md")

    assert "Ratification outcome (2026-07-22)" in plan
    assert "micro-randomized exposure-response instrument" in plan
    assert "Branch B remains the mechanical fail branch" in plan
    assert "design ratified conditionally" in design
    assert "R_reply" in design
    assert "does not" in design and "H1b" in design


def test_plan_does_not_gate_development_on_external_prerequisites():
    plan = _read("IMPLEMENTATION_PLAN.md")
    instrument_design = _read(
        "results/s3_probe/2026-07-22_oasis_causal_probe_design_review.md"
    )

    assert "Nebentätig" not in plan
    assert "supervisor-defined PhD milestone" not in plan
    assert "Stage-2 hard preconditions" not in plan
    assert "Repository development is not gated by external employment or milestone records" in plan
    assert "Nebentätigkeitsanzeige" not in instrument_design
    assert "external prerequisite" not in instrument_design.lower()


def test_stage1_fallback_archive_is_explicitly_retrospective():
    report = _read(
        "results/s0.4_feasibility/2026-06-27_stage1_data_validity_report.md"
    )

    assert "Repository archive status: retrospective" in report
    assert "does not provide git-visible freeze-before-measure evidence" in report
    assert "No trustworthy per-market `n` is banked" in report


def test_each_stage1_supporting_record_discloses_retrospective_archival():
    supporting_records = (
        "results/s0.4_feasibility/2026-06-25_dual_capture_merge_rule.md",
        "results/s0.4_feasibility/2026-06-25_fragment_salvage_gof.md",
        "results/s0.4_feasibility/2026-06-25_fragment_salvage_rule.md",
        "results/s0.4_feasibility/2026-06-26_dual_capture_gof_1128_1197.md",
        "results/s0.4_feasibility/2026-06-26_dual_capture_gof_7223_0340_0001_9698.md",
    )

    for relative_path in supporting_records:
        record = _read(relative_path)
        assert "Repository archive status: retrospective" in record, relative_path
