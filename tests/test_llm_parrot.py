"""Fast synthetic tests for the matched-null generator + isolation gate (sub-inc-2 T6).
No torch: pool embeddings are hand-built unit vectors. Every gate failure path is POWER-CHECKED
with a planted violation (the sub-inc-1 'DID NOT RAISE' discipline)."""
import numpy as np
import pytest

from critaudit.cascades.extract import post_reply_tree
from critaudit.sim.harness.cohort_marginals import CohortMarginals
from critaudit.sim.harness.types import HarnessRun
from critaudit.sim.controls.llm_parrot import check_matched_null_control, generate_matched_null


def _unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def _toy_pool(n=6, dim=8, seed=1):
    # ANISOTROPIC toy vectors (shared direction + noise) — the geometry real sentence embeddings
    # actually have (MiniLM pool means are large). The gate's MATCH_EMBED_MEAN_COS_MIN floor is a
    # sample-size formula that PRESUMES this: with isotropic random unit vectors the pool mean is
    # ~0 and a tiny resample's mean-cosine is unstable at any threshold (observed 0.68 at n=6
    # while building this test) — that is the toy violating the gate's operating regime, not a
    # gate defect.
    rng = np.random.default_rng(seed)
    shared = np.ones(dim)
    E = shared + 0.3 * rng.normal(size=(n, dim))
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    texts = tuple(f"msg-{i:02d}-" + "x" * (i % 4) for i in range(n))
    return texts, E


def _toy_marginals():
    texts, E = _toy_pool()
    return CohortMarginals(per_round_counts=(2, 1, 0, 3), authored_texts=texts), E


def test_generator_deterministic_and_wellformed():
    marg, E = _toy_marginals()
    r1 = generate_matched_null(11, marg, E, 0.5, window=2)
    r2 = generate_matched_null(11, marg, E, 0.5, window=2)
    assert np.array_equal(r1.times, r2.times)
    assert np.array_equal(r1.parent_idx, r2.parent_idx)
    assert r1.content == r2.content                      # same seed -> identical stream
    assert isinstance(r1, HarnessRun)
    # times = round index repeated per-count; zero-count round 2 absent from the stream.
    assert r1.times.tolist() == [0.0, 0.0, 1.0, 3.0, 3.0, 3.0]
    assert int(r1.read_emit_success.sum()) == 0          # no read channel exists
    assert all(c in marg.authored_texts for c in r1.content)
    av = post_reply_tree(r1.times, r1.root_id, r1.parent_idx)   # invariants by construction
    assert int(av.sizes.sum()) == 6


def test_generator_seed_varies_content_stream():
    marg, E = _toy_marginals()
    draws = {tuple(generate_matched_null(s, marg, E, 0.5, window=2).content) for s in range(8)}
    assert len(draws) > 1                                # the namespaced stream actually varies


def test_generator_fail_closed():
    marg, E = _toy_marginals()
    with pytest.raises(ValueError, match="misaligned"):
        generate_matched_null(1, marg, E[:-1], 0.5, window=2)  # pool/embedding misalignment
    empty = CohortMarginals(per_round_counts=(0, 0), authored_texts=marg.authored_texts)
    with pytest.raises(ValueError, match="empty per-round profile"):
        generate_matched_null(1, empty, E, 0.5, window=2)


def test_gate_passes_on_generated_null_and_records_structure():
    marg, E = _toy_marginals()
    run = generate_matched_null(11, marg, E, 0.5, window=2)
    diag = check_matched_null_control(run, marg, E)
    assert diag["n_events"] == 6
    assert 0.0 <= diag["n_struct"] < 1.0                 # recorded, never asserted against a band
    assert diag["ks_len_stat"] <= diag["ks_len_bound"]
    assert diag["mean_embed_cos"] >= 0.98
    assert len(diag["fano"]) == 3


def test_gate_trips_on_injected_read_emit_success():
    marg, E = _toy_marginals()
    run = generate_matched_null(11, marg, E, 0.5, window=2)
    run.read_emit_success[2] = True                      # planted residual coupling
    with pytest.raises(AssertionError, match="decoupling tripwire"):
        check_matched_null_control(run, marg, E)


def test_gate_trips_on_doctored_per_round_counts():
    marg, E = _toy_marginals()
    run = generate_matched_null(11, marg, E, 0.5, window=2)
    run.times[-1] = 2.0                                  # move an event into the empty round
    with pytest.raises(AssertionError, match="per-round counts"):
        check_matched_null_control(run, marg, E)


def test_gate_trips_on_non_round_granular_times():
    # Review 2026-07-17: a corrupted clock (1.5) must trip the gate, not truncate back into an
    # 'exact' count match via astype.
    marg, E = _toy_marginals()
    run = generate_matched_null(11, marg, E, 0.5, window=2)
    run.times[2] = 1.5
    with pytest.raises(AssertionError, match="round-granular"):
        check_matched_null_control(run, marg, E)


def test_gate_trips_on_length_marginal_mismatch():
    # Larger n so the sample-size KS bound has power (at n=6 the DKW-scale bound saturates > 1 and
    # structurally cannot trip — that is the formula working as designed, not a gap).
    rng = np.random.default_rng(3)
    n = 120
    E = rng.normal(size=(n, 8))
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    short = CohortMarginals(per_round_counts=(40, 40, 40),
                            authored_texts=tuple("s" * 5 for _ in range(n)))
    long = CohortMarginals(per_round_counts=(40, 40, 40),
                           authored_texts=tuple("L" * 50 for _ in range(n)))
    run = generate_matched_null(7, short, E, 0.5, window=2)
    with pytest.raises(AssertionError, match="length KS"):
        check_matched_null_control(run, long, E)         # doctored pool: KS trips before lookup


def test_gate_trips_on_embedding_marginal_mismatch():
    # Hand-built null that passes counts (exact) and KS (identical lengths) but is embedding-
    # skewed: every event resamples the one outlier text whose vector opposes the pool mean.
    texts = tuple(f"tt{i}" for i in range(5)) + ("out",)          # all length-3, KS = 0
    E = np.stack([_unit([1, 0.1 * i, 0]) for i in range(5)] + [_unit([-1, 0, 0])])
    marg = CohortMarginals(per_round_counts=(2, 2), authored_texts=texts)
    n = 4
    run = HarnessRun(times=np.array([0.0, 0.0, 1.0, 1.0]),
                     root_id=np.arange(n, dtype=np.int64),
                     parent_idx=np.full(n, -1, dtype=np.int64),
                     read_emit_success=np.zeros(n, dtype=bool),
                     content=["out"] * n)
    with pytest.raises(AssertionError, match="mean-embedding cosine"):
        check_matched_null_control(run, marg, E)


def test_gate_trips_on_content_outside_pool():
    marg, E = _toy_marginals()
    run = generate_matched_null(11, marg, E, 0.5, window=2)
    run.content[0] = "not-in-pool"
    with pytest.raises(AssertionError, match="authored pool"):
        check_matched_null_control(run, marg, E)


@pytest.mark.parametrize("field", ["root_id", "parent_idx", "read_emit_success", "content"])
def test_gate_rejects_every_misaligned_event_field(field):
    marg, E = _toy_marginals()
    run = generate_matched_null(11, marg, E, 0.5, window=2)
    value = getattr(run, field)
    setattr(run, field, value[:-1])
    with pytest.raises(AssertionError, match="misaligned"):
        check_matched_null_control(run, marg, E)


def test_gate_rejects_non_boolean_read_flags_even_when_sum_is_zero():
    marg, E = _toy_marginals()
    run = generate_matched_null(11, marg, E, 0.5, window=2)
    run.read_emit_success = np.array([1, -1, 0, 0, 0, 0])
    with pytest.raises(AssertionError, match="boolean"):
        check_matched_null_control(run, marg, E)


@pytest.mark.parametrize("bad", ["nonfinite", "not normalized"])
def test_gate_rejects_invalid_pool_embeddings(bad):
    marg, E = _toy_marginals()
    run = generate_matched_null(11, marg, E, 0.5, window=2)
    E = E.copy()
    if bad == "nonfinite":
        E[0, 0] = np.nan
    else:
        E[0] *= 2
    with pytest.raises(AssertionError, match=bad):
        check_matched_null_control(run, marg, E)
