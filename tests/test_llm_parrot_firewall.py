"""The τ-arm firewall (sub-inc-2 design 2026-07-17 §8) — STRUCTURAL embargo enforcement, all
@fast, always in CI. Precedent: the textual cross-file tripwires of
test_task10_spec_freezes_present_and_sane.

Four guards: (1) AST scan — the sub-inc-2 modules import no fitting stack and reference no τ-arm
symbol; (2) banked-artifact schema — the committed JSONs carry no embargoed key; (3) the
CohortMarginals whitelist; (4) defined-not-evaluated — the §9 criteria exist in the spec and are
referenced by NO sub-inc-2 module. A red here means the embargo was breached in code, before any
result could be interpreted."""
import ast
import json
import os
import re

from conftest import names_and_imports as _names_and_imports_impl
from critaudit.sim.controls import llm_parrot_spec as lps
from critaudit.sim.harness.cohort_marginals import COHORT_MARGINALS_FIELDS

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The sub-inc-2 modules under embargo (design §8): the EXPLICIT minimum-coverage list, unioned
# with every module under src/critaudit that imports the sub-inc-2 surface (llm_parrot_spec or
# cohort_marginals) — so a future module that self-identifies as sub-inc-2 surface cannot
# silently escape the scan by not being appended here (review 2026-07-17: a hand-maintained list
# was a completeness hole; nothing failed when you forgot to extend it).
_SCANNED_MINIMUM = [
    "src/critaudit/cascades/similarity.py",
    "src/critaudit/sim/harness/cohort_marginals.py",
    "src/critaudit/sim/harness/embedding.py",
    "src/critaudit/sim/controls/llm_parrot.py",
    "src/critaudit/experiments/llm_parrot_null.py",
]
_SURFACE_MARKERS = ("llm_parrot_spec", "cohort_marginals")


def _discover_scanned():
    found = set()
    src_root = os.path.join(_REPO, "src", "critaudit")
    for dirpath, _, files in os.walk(src_root):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, _REPO)
            if rel.replace(os.sep, "/").endswith(
                    ("controls/llm_parrot_spec.py", "harness/cohort_marginals.py")):
                found.add(rel.replace(os.sep, "/"))    # the surface itself is always scanned
                continue
            tree = ast.parse(open(path).read(), filename=path)
            for node in ast.walk(tree):
                # Both import shapes count: `import ...llm_parrot_spec` (module path carries the
                # marker) and `from critaudit.sim.controls import llm_parrot_spec` (the marker is
                # the imported NAME).
                refs = []
                if isinstance(node, ast.Import):
                    refs = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    refs = [node.module or ""] + [a.name for a in node.names]
                if any(r and any(mark in r for mark in _SURFACE_MARKERS) for r in refs):
                    found.add(rel.replace(os.sep, "/"))
                    break
    return sorted(found)


_SCANNED = sorted(set(_SCANNED_MINIMUM) | set(_discover_scanned()))


def test_scan_set_discovery_covers_the_minimum():
    # The discovery must independently find every explicitly-listed module (proves the dynamic
    # sweep works; if discovery breaks, this reds rather than the scan silently narrowing).
    discovered = set(_discover_scanned())
    missing = [p for p in _SCANNED_MINIMUM if p not in discovered]
    assert not missing, f"discovery failed to find {missing} — the dynamic sweep is broken"

# Forbidden import roots (the fitting stack) and symbols (the τ-arm), verified against the real
# package layout: critaudit.powerlaw (fit_powerlaw), critaudit.hawkes (certify_near_critical),
# critaudit.scaling (exponents), experiments.parrot_null (read_tau_arm).
_FORBIDDEN_MODULES = ("critaudit.powerlaw", "critaudit.hawkes", "critaudit.scaling")
_FORBIDDEN_NAMES = {"read_tau_arm", "fit_powerlaw", "certify_near_critical", "exponents"}

# Defined-not-evaluated (§9): frozen in the spec module, referenced by NOTHING in sub-inc 2.
_EMBARGOED_CONSTANTS = {"NULL_TAU_FRAC_MAX", "N_EMIT_DEFINITION"}


def _names_and_imports(path):
    return _names_and_imports_impl(_REPO, path)


def test_no_fitting_stack_import_or_tau_arm_reference():
    for path in _SCANNED:
        imports, names = _names_and_imports(path)
        for mod in imports:
            assert not any(mod == f or mod.startswith(f + ".") for f in _FORBIDDEN_MODULES), (
                f"{path} imports embargoed module {mod!r} (design §8)")
        hit = names & _FORBIDDEN_NAMES
        assert not hit, f"{path} references embargoed symbol(s) {sorted(hit)} (design §8)"


def test_defined_not_evaluated_constants_unreferenced():
    # The §9 criteria are FROZEN (present in the spec module — asserted in test_llm_parrot_spec)
    # and EVALUATED NOWHERE: no sub-inc-2 module even names them.
    assert hasattr(lps, "NULL_TAU_FRAC_MAX") and hasattr(lps, "N_EMIT_DEFINITION")
    spec_module = "src/critaudit/sim/controls/llm_parrot_spec.py"
    for path in _SCANNED:
        if path == spec_module:
            continue                                   # the spec DEFINES them; consumers may not
        _, names = _names_and_imports(path)
        hit = names & _EMBARGOED_CONSTANTS
        assert not hit, f"{path} references defined-not-evaluated constant(s) {sorted(hit)}"


def test_scanner_has_power_on_a_known_violator():
    # POWER CHECK (the 'DID NOT RAISE' discipline): the scanner must FLAG a module that really
    # does reference the τ-arm — the prototype rig itself (experiments/parrot_null.py defines
    # read_tau_arm and calls fit_powerlaw). If this stops flagging, the scan is blind and every
    # green above is meaningless.
    imports, names = _names_and_imports("src/critaudit/experiments/parrot_null.py")
    fitting_import = any(mod == f or mod.startswith(f + ".")
                         for mod in imports for f in _FORBIDDEN_MODULES)
    assert fitting_import or (names & _FORBIDDEN_NAMES)


def test_cohort_marginals_whitelist():
    # The ONLY surface through which cohort data reaches the generator: exactly two fields,
    # nothing a tree statistic could ride in on.
    assert COHORT_MARGINALS_FIELDS == ("per_round_counts", "authored_texts")


from critaudit.experiments.llm_parrot_null import BANKED_DIR as _BANKED_DIR  # single source
_EMBARGOED_KEY = re.compile(r"tau|p_boot|alpha|gate_|n_emit")


def _all_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_keys(v)


def test_banked_artifacts_carry_no_embargoed_keys():
    banked = sorted(f for f in os.listdir(_BANKED_DIR) if f.endswith(".json"))
    assert banked, "no banked sub-inc-2 artifacts found — firewall has nothing to guard"
    for name in banked:
        with open(os.path.join(_BANKED_DIR, name)) as f:
            record = json.load(f)
        bad = sorted({k for k in _all_keys(record) if _EMBARGOED_KEY.search(k)})
        assert not bad, f"{name} carries embargoed key(s) {bad} (design §8)"
