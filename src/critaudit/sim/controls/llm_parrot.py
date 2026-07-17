"""The MATCHED parrot null generator + its isolation gate (sub-inc-2 design 2026-07-17 §7).

Belief-decoupling is STRUCTURAL: `generate_matched_null` takes only (seed, marginals,
pool_embeddings, theta, spec) — there is no field a read channel, a served set, or a per-agent
rate could enter through. CohortMarginals is the whitelisted two-field firewall surface; whatever
reply structure the output exhibits is emergent from content statistics alone under the frozen
attribution rule. The do-not-match list binds: branching, avalanche sizes, and per-agent rates
are never matched (the null carries no agent identity at all).

The gate (`check_matched_null_control`) is the §6-gate analog of `simulate_parrot`'s
`successes == 0` tripwire: fail-closed, three clauses (decoupling tripwire / matching quality /
well-formedness), raising on any failure — a failed gate blocks interpretation, never returns a
flattering diagnostic. `check_positive_control` explicitly does NOT apply to the null: its
read_emit_ratio floor asserts coupling PRESENT, which the null must lack."""
from __future__ import annotations
import numpy as np

from critaudit.cascades.extract import post_reply_tree
from critaudit.cascades.similarity import attribute_similarity_parents
from critaudit.sim.controls import llm_parrot_spec as lps
from critaudit.sim.controls.anchors import burstiness, fano_profile, n_struct
from critaudit.sim.harness.types import HarnessRun


def generate_matched_null(seed, marginals, pool_embeddings, theta, *, spec=lps):
    """One matched-null stream (design §7): times = round index r repeated c_r times (the
    cohort window's per-round aggregate counts copied EXACTLY — the substrate-imposed cadence
    including the real declining ramp); content = uniform with-replacement resample of the
    window's authored pool (repost '' entries included) on the namespaced content stream;
    embeddings LOOKED UP by pool index (no re-encoding — exactly marginal-matched); edges by the
    frozen attribution rule at the calibrated theta; read_emit_success all-False (no read channel
    exists). Returns a HarnessRun satisfying post_reply_tree's invariants by construction."""
    pool_embeddings = np.asarray(pool_embeddings)
    counts = np.asarray(marginals.per_round_counts, dtype=np.int64)
    pool = list(marginals.authored_texts)
    if pool_embeddings.ndim != 2 or pool_embeddings.shape[0] != len(pool):
        raise ValueError(
            f"pool embeddings ({pool_embeddings.shape}) misaligned with authored pool "
            f"({len(pool)}) — wrong window or wrong field embedded (fail-closed)")
    if counts.sum() <= 0:
        raise ValueError("empty per-round profile (fail-closed)")

    rng = np.random.default_rng(
        np.random.SeedSequence(seed, spawn_key=(spec.NULL_STREAM_CONTENT,)))
    n = int(counts.sum())
    # One stream-order draw realizes the frozen per-round uniform resample (the per-round split
    # is positional: event k of round r is draw position offset(r)+k).
    drawn = rng.integers(0, len(pool), size=n)

    round_of = np.repeat(np.arange(counts.size), counts)
    times = round_of.astype(float)
    E_stream = pool_embeddings[drawn]
    parent_idx, root_id = attribute_similarity_parents(round_of, E_stream, theta, spec=spec)
    return HarnessRun(times=times, root_id=root_id, parent_idx=parent_idx,
                      read_emit_success=np.zeros(n, dtype=bool),
                      content=[pool[i] for i in drawn])


def check_matched_null_control(null_run, marginals, pool_embeddings, *, spec=lps):
    """Fail-closed isolation gate, three clauses (design §7). Raises AssertionError on any
    failure (blocks interpretation); returns the recorded diagnostics dict on pass.

    (i)  DECOUPLING TRIPWIRE: read_emit_success.sum() == 0 — enforcement over assumption,
         mirroring simulate_parrot's successes == 0.
    (ii) MATCHING QUALITY (frozen sample-size formulas, construction-bug detectors): per-round
         counts == the window's EXACTLY (a copy — tolerance zero); two-sample KS on authored
         lengths <= MATCH_LEN_KS_COEFF*sqrt((n+m)/(n*m)); cosine(mean null embedding, mean pool
         embedding) >= MATCH_EMBED_MEAN_COS_MIN.
    (iii) WELL-FORMED: post_reply_tree consumes without error; n_struct/burstiness/fano_profile
         evaluate — values RECORDED, not asserted (the null's structure is free by design).

    KNOWN LIMIT (disclosed): clause (ii)'s embedding check reconstructs the null's embeddings by
    TEXT lookup (first pool occurrence per distinct text), so it verifies the embedding MARGINAL,
    not which pool rows the generator consumed — a drawn-index/content desynchronization inside
    the generator is not detectable from the run alone (guarded instead by the generator's single
    `drawn` array and its determinism tests)."""
    from scipy.stats import ks_2samp

    # All clauses use explicit `raise AssertionError` (the positive_control.py idiom), NEVER bare
    # `assert`: a fail-closed gate must survive `python -O` / PYTHONOPTIMIZE, which strips asserts
    # (review finding 2026-07-17).
    times = np.asarray(null_run.times, dtype=float)
    n = times.size
    if n == 0:
        raise AssertionError("matched-null gate: empty stream (fail-closed)")

    # (i) decoupling tripwire
    n_read = int(np.asarray(null_run.read_emit_success).sum())
    if n_read != 0:
        raise AssertionError(
            f"matched-null gate: decoupling tripwire — {n_read} read->emit successes in a null "
            f"with no read channel (residual coupling or a construction bug)")

    # (ii) matching quality. Round-granularity is validated BEFORE binning — astype truncation
    # would otherwise fold a corrupted clock (1.5 -> round 1) back into an 'exact' count match.
    rounds = np.floor(times).astype(np.int64)
    if not np.all(times == rounds) or (n and rounds.min() < 0):
        raise AssertionError(
            "matched-null gate: non-round-granular or negative event times (corrupted clock)")
    counts = np.asarray(marginals.per_round_counts, dtype=np.int64)
    got = np.bincount(rounds, minlength=counts.size)
    if not np.array_equal(got, counts):
        raise AssertionError(
            "matched-null gate: per-round counts differ from the matched window's "
            "(exact-copy rule)")

    len_null = np.array([len(c) for c in null_run.content], dtype=float)
    len_pool = np.array([len(c) for c in marginals.authored_texts], dtype=float)
    ks = float(ks_2samp(len_null, len_pool).statistic)
    ks_bound = spec.MATCH_LEN_KS_COEFF * np.sqrt(
        (len_null.size + len_pool.size) / (len_null.size * len_pool.size))
    if ks > ks_bound:
        raise AssertionError(
            f"matched-null gate: authored-length KS {ks:.4f} > bound {ks_bound:.4f} "
            f"(wrong pool or wrong field)")

    pool_embeddings = np.asarray(pool_embeddings)
    lookup = {}
    for text, row in zip(marginals.authored_texts, pool_embeddings):
        lookup.setdefault(text, row)
    try:
        E_null = np.stack([lookup[c] for c in null_run.content])
    except KeyError as e:
        raise AssertionError(
            f"matched-null gate: null content {e} not in the matched window's authored pool")
    mu_null = E_null.mean(axis=0)
    mu_pool = pool_embeddings.mean(axis=0)
    denom = float(np.linalg.norm(mu_null) * np.linalg.norm(mu_pool))
    if denom <= 0:
        raise AssertionError("matched-null gate: degenerate mean embedding")
    mean_cos = float(mu_null @ mu_pool / denom)
    if mean_cos < spec.MATCH_EMBED_MEAN_COS_MIN:
        raise AssertionError(
            f"matched-null gate: mean-embedding cosine {mean_cos:.4f} < "
            f"{spec.MATCH_EMBED_MEAN_COS_MIN} (embedding-marginal mismatch)")

    # (iii) well-formed; structure RECORDED, never asserted
    av = post_reply_tree(times, null_run.root_id, null_run.parent_idx)
    horizon = float(counts.size)
    diag = {
        "n_events": int(n),
        "n_roots": int(av.sizes.size),
        "n_struct": float(n_struct(av)),
        "burstiness": float(burstiness(times)),
        "fano": [float(f) for f in fano_profile(times, horizon, spec.NULL_FANO_WINDOW_SIZES)],
        "ks_len_stat": ks,
        "ks_len_bound": float(ks_bound),
        "mean_embed_cos": mean_cos,
    }
    return diag
