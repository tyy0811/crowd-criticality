# tests/test_parrot_v2_source_pins.py
import hashlib, subprocess

FROZEN = {
    "src/critaudit/sim/controls/llm_parrot_spec.py":
        "4596e934290adff429efc3800e9013463c24619d3212f7ca189fed3b519be85b",
    "src/critaudit/sim/harness/cohort_marginals.py":
        "20f9257135841d5d30b07b324dc2102ce9c13a822a0608b1a1ac8ad198590e35",
    "src/critaudit/sim/harness/harness_spec.py":
        "472defb93d0ccda3c290b6c7909f17cdcb0af639c2d83517ee11f35ebd21abcd",
    # Updated 2026-08-17/18 three times, each owner-authorized and append-only
    # at EOF (§§0-10 byte-untouched throughout): the prospective §11 registration
    # (9a65f28eff3f9e37afe514641a06c6a61d3dad222d7bc4ecbd5a1e6b5c663bab, prior
    # 996c42228da1a18771c6343b92b3c0fca8f1849a9ce70bc8af115cbb764eaa35), the §11
    # R3 measurement record (d8b694be39e93f72c0f7c5eeb3a1996f2c98a7e523a05a103ef7eed2cf353813),
    # then the 2026-08-18 owner-review wording correction (cohort comparison).
    "PRE_REGISTRATION.md":
        "630617cbdf971a6118afe0494987a434fb595e1a7d7e99ebcbb6c29616438135",
}

def test_frozen_surfaces_unchanged():
    for path, expected in FROZEN.items():
        actual = hashlib.sha256(open(path, "rb").read()).hexdigest()
        assert actual == expected, f"{path} drifted (frozen surface)"

def test_src_never_imports_tests():
    out = subprocess.run(["grep", "-rn", "-E", "from tests|import tests", "src/"],
                         capture_output=True, text=True)
    assert out.stdout == ""

def test_v2_modules_not_imported_by_production_probe_or_harness():
    out = subprocess.run(
        ["grep", "-rln", "parrot_v2",
         "src/critaudit/experiments/causal_probe_recoverability.py",
         "src/critaudit/sim/harness/oasis_adapter.py",
         "src/critaudit/sim/harness/harness_spec.py"],
        capture_output=True, text=True)
    assert out.stdout == ""
