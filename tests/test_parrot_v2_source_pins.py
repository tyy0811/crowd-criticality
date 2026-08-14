# tests/test_parrot_v2_source_pins.py
import hashlib, subprocess

FROZEN = {
    "src/critaudit/sim/controls/llm_parrot_spec.py":
        "4596e934290adff429efc3800e9013463c24619d3212f7ca189fed3b519be85b",
    "src/critaudit/sim/harness/cohort_marginals.py":
        "20f9257135841d5d30b07b324dc2102ce9c13a822a0608b1a1ac8ad198590e35",
    "src/critaudit/sim/harness/harness_spec.py":
        "472defb93d0ccda3c290b6c7909f17cdcb0af639c2d83517ee11f35ebd21abcd",
    "PRE_REGISTRATION.md":
        "996c42228da1a18771c6343b92b3c0fca8f1849a9ce70bc8af115cbb764eaa35",
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
