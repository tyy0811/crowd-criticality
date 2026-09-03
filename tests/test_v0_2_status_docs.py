from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = ROOT / "docs/V0_2_ACTIVITY_BACKTEST.md"


def test_v0_2_boundary_is_explicit_and_disjoint():
    text = BOUNDARY.read_text(encoding="utf-8")
    for required in (
        "retrospective screening study",
        "forward shadow replication is the adjudicating test",
        "no criticality claim",
        "no H1b credit",
        "no OASIS regime-placement credit",
        "Stage 3 remains closed",
        "USD 20",
        "USD 5",
    ):
        assert required in text


def test_v0_2_boundary_names_all_comparison_arms():
    text = BOUNDARY.read_text(encoding="utf-8")
    assert all(name in text for name in ("M0", "M1", "M2", "M3Q", "M3P"))
    assert "M3P must beat M3Q" in text


def test_v0_2_boundary_protects_the_running_recorder():
    text = BOUNDARY.read_text(encoding="utf-8")
    assert "com.crowdcriticality.brecorder" in text
    assert "must not be stopped, modified, or replaced" in text


def test_v0_2_boundary_requires_paid_gemini_and_forbids_free_post_submission():
    text = BOUNDARY.read_text(encoding="utf-8")
    assert "paid Gemini tier is required before any post text is submitted" in text
    assert "post text must not be sent on Gemini's free tier" in text


def test_v0_2_recorder_continuation_is_a_separate_open_decision():
    decisions = (ROOT / "DECISIONS.md").read_text(encoding="utf-8")
    assert "1.0 GB" in decisions
    assert "continuing capture is not scientific authorization" in decisions
    assert "separate owner decision" in decisions
