import base64
from critaudit.sim.harness.types import EventRecord
from critaudit.sim.controls.parrot_v2_records import emission_record_bytes
from critaudit.sim.controls.parrot_v2_compare import (
    manipulation_guard, overall_verdict, schedule_verdict, violator_verdict)


def _ev(i, t, a, parent, content, seq):
    return EventRecord(item_id=i, time=t, agent_id=a, parent_item_id=parent,
                       content=content, seq=seq)

def _led(idx, agent, rnd, outcome, served, seq):
    return {"schedule_index": idx, "agent_id": agent, "round": rnd,
            "outcome": outcome, "served_item_ids": served, "trace_seq": seq}

def _payload(events, width, ledger):
    return {"emission_record_b64":
                base64.b64encode(emission_record_bytes(events)).decode(),
            "width": width, "refresh_ledger": ledger,
            "observables": {"n_events": len(events), "frac_size1": 1.0,
                             "giant_frac": 1.0 / max(len(events), 1),
                             "length_spread": 0.0, "read_emit_ratio": 0.1 * width}}

BASE = [_ev("post:1", 0.0, 3, None, "alpha", 1)]
L_A = [_led(0, 3, 0, "served", ["post:1"], 2)]
L_B = [_led(0, 3, 0, "served", ["post:1", "post:2"], 2)]
L_EMPTY = [_led(0, 3, 0, "empty", [], None)]
L_MISALIGNED = [_led(0, 4, 0, "served", ["post:1"], 2)]      # wrong agent at index

def _triple(l1, l3, l5, e1=BASE, e3=BASE, e5=BASE):
    return {1: _payload(e1, 1, l1), 3: _payload(e3, 3, l3), 5: _payload(e5, 5, l5)}


def test_guard_contrast_alignment_and_flip():
    g = manipulation_guard(_triple(L_A, L_B, L_B))
    assert g["ok"] and g["realized_contrast"] and g["paired_served_differences"] >= 1
    g2 = manipulation_guard(_triple(L_A, L_A, L_A))
    assert g2["ok"] and g2["realized_contrast"] is False      # -> R3 downstream
    g3 = manipulation_guard(_triple(L_A, L_MISALIGNED, L_A))
    assert g3["ok"] is False and g3["realized_contrast"] is False   # NEVER contrast
    g4 = manipulation_guard(_triple(L_A, L_EMPTY, L_A))       # outcome flip
    assert g4["ok"] is False and g4["realized_contrast"] is False


def test_schedule_verdict_gated_only_and_read_emit_ignored():
    v = schedule_verdict(_triple(L_A, L_B, L_B))
    assert v["invariant"] is True         # read_emit_ratio differs by width; ignored
    broken = schedule_verdict(_triple(
        L_A, L_B, L_B, e3=[_ev("post:1", 0.0, 3, None, "beta", 1)]))
    assert broken["invariant"] is False and broken["first_divergence"] is not None


def test_violator_verdict_pairwise():
    # pairs with served differences: (1,3) and (1,5); pair (3,5) has none.
    ok = violator_verdict(_triple(
        L_A, L_B, L_B,
        e3=[_ev("post:1", 0.0, 3, None, "HASHX", 1)],
        e5=[_ev("post:1", 0.0, 3, None, "HASHY", 1)]))
    assert ok["ok"] is True
    # fully blind: every contrasting pair has byte-equal records
    blind = violator_verdict(_triple(L_A, L_B, L_B))
    assert blind["ok"] is False and blind["reason"].startswith("blind_pair")
    # PLANTED WRONG PAIR: (1,5) differs properly, but (1,3) has served contrast
    # with byte-equal records -> must fail on exactly that pair
    wrong_pair = violator_verdict(_triple(
        L_A, L_B, L_B,
        e5=[_ev("post:1", 0.0, 3, None, "HASHY", 1)]))   # e1 == e3 == BASE
    assert wrong_pair["ok"] is False
    assert wrong_pair["reason"] == "blind_pair:(1,3)"


def test_precedence_r3_over_r2():
    clean_guard = {"ok": True, "failure": None, "realized_contrast": True,
                   "paired_served_differences": 1}
    bad_guard = {"ok": False, "failure": "misaligned", "realized_contrast": False,
                 "paired_served_differences": 0}
    no_contrast = {"ok": True, "failure": None, "realized_contrast": False,
                   "paired_served_differences": 0}
    broken = {"invariant": False, "first_divergence": {"field": "content"},
              "guard": clean_guard}
    ok = {"invariant": True, "first_divergence": None, "guard": clean_guard}
    # R2: all guards clean-with-contrast, one break
    assert overall_verdict([broken, ok], [{"ok": True, "reason": None}])["reading"] == "R2"
    # R3 DOMINATES R2: same break + one guard failure elsewhere
    r = overall_verdict([broken, {"invariant": True, "first_divergence": None,
                                  "guard": bad_guard}],
                        [{"ok": True, "reason": None}])
    assert r["reading"] == "R3"
    # R3 via no-contrast, with wording
    r2 = overall_verdict([{"invariant": True, "first_divergence": None,
                           "guard": no_contrast}], [{"ok": True, "reason": None}])
    assert r2["reading"] == "R3"
    assert "no realized exposure contrast" in r2["detail"]
    # R3 via run failure even when everything else is clean
    assert overall_verdict([ok], [{"ok": True, "reason": None}],
                           run_failures=("w3 crashed",))["reading"] == "R3"
    # R1 when everything is clean
    assert overall_verdict([ok], [{"ok": True, "reason": None}])["reading"] == "R1"


def test_guard_rejects_non_frozen_width_set():
    # missing a frozen width
    partial = {1: _payload(BASE, 1, L_A), 3: _payload(BASE, 3, L_B)}
    g = manipulation_guard(partial)
    assert g["ok"] is False and g["realized_contrast"] is False
    # wrong member, internally self-consistent
    wrong = {1: _payload(BASE, 1, L_A), 3: _payload(BASE, 3, L_B),
             7: _payload(BASE, 7, L_B)}
    g2 = manipulation_guard(wrong)
    assert g2["ok"] is False and g2["realized_contrast"] is False
