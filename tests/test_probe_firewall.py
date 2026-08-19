"""Probe firewall (sub-inc-3 T7, fast, CI): the probe modules import neither the sub-inc-2
surface (llm_parrot_spec/cohort_marginals — would join that increment's self-discovering scan
set, R8) nor any fitting stack, and reference no retired §9 / τ-arm symbol. The probe study
legitimately reads seeded SIZES and SUCCESSES from its own ABM runs — nothing else; §9a/§9b are
retired-as-blocked, so no sub-inc-3 module may compute τ on anything. Banked results/s3_probe
JSONs carry no embargoed key. Scanner power-checked against a known violator."""
import json
import os
import re

from conftest import names_and_imports as _names_and_imports_impl

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_SCANNED = [
    "src/critaudit/sim/controls/probe.py",
    "src/critaudit/sim/controls/probe_spec.py",
    "src/critaudit/sim/controls/probe_gate.py",
    "src/critaudit/experiments/probe_recoverability.py",
]
_OPTIONAL = ["src/critaudit/experiments/probe_pilot_oasis.py"]   # scanned once it exists

_FORBIDDEN_MODULES = ("critaudit.powerlaw", "critaudit.hawkes", "critaudit.scaling")
_FORBIDDEN_NAMES = {"read_tau_arm", "fit_powerlaw", "certify_near_critical", "exponents",
                    "NULL_TAU_FRAC_MAX", "N_EMIT_DEFINITION",
                    "llm_parrot_spec", "cohort_marginals"}


def _names_and_imports(path):
    return _names_and_imports_impl(_REPO, path)


def _scan_targets():
    return _SCANNED + [p for p in _OPTIONAL if os.path.isfile(os.path.join(_REPO, p))]


def test_probe_modules_clean_of_fitting_stack_and_subinc2_surface():
    for path in _scan_targets():
        imports, names = _names_and_imports(path)
        for mod in imports:
            assert not any(mod == f or mod.startswith(f + ".") for f in _FORBIDDEN_MODULES), \
                f"{path} imports embargoed module {mod!r}"
            assert "llm_parrot" not in mod and "cohort_marginals" not in mod, \
                f"{path} imports the sub-inc-2 surface ({mod!r}) — R8"
        hit = names & _FORBIDDEN_NAMES
        assert not hit, f"{path} references embargoed symbol(s) {sorted(hit)}"


def test_scanner_has_power_on_known_violators():
    # The prototype rig references the tau-arm; the sub-inc-2 driver imports its surface.
    imports, names = _names_and_imports("src/critaudit/experiments/parrot_null.py")
    assert (names & _FORBIDDEN_NAMES) or any(
        m.startswith("critaudit.powerlaw") for m in imports)
    imports2, names2 = _names_and_imports("src/critaudit/experiments/llm_parrot_null.py")
    assert any("llm_parrot" in m for m in imports2) or ("llm_parrot_spec" in names2)


_BANKED_DIR = os.path.join(_REPO, "results", "s3_probe")
_EMBARGOED_KEY = re.compile(r"tau|p_boot|alpha|gate_|n_emit")


def _all_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_keys(v)


def test_banked_probe_artifacts_carry_no_embargoed_keys():
    if not os.path.isdir(_BANKED_DIR):
        return                                            # nothing banked yet (pre-T9)
    for name in sorted(f for f in os.listdir(_BANKED_DIR) if f.endswith(".json")):
        with open(os.path.join(_BANKED_DIR, name)) as f:
            record = json.load(f)
        bad = sorted({k for k in _all_keys(record) if _EMBARGOED_KEY.search(k)})
        assert not bad, f"{name} carries embargoed key(s) {bad}"
