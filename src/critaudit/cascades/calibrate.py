"""Result-blind Gate-D recovery for #3's bin-width knob. Plant a temporally-SEPARABLE labeled stream
(sparse immigrants), then for each k in spec.TAU_Q_GRID score how well timing-only binning recovers the
generator's tree membership (ARI vs root_id). The frozen rule (spec.py) selects argmax-ARI; the value is
written into spec.TAU_Q_K. No threshold is computed here — it is read from spec."""
from __future__ import annotations
import numpy as np
from critaudit.cascades.ground_truth import labeled_stream
from critaudit.cascades.extract import _avalanche_labels, bin_width
from critaudit.cascades import spec

# Separable regime: low immigrant rate so temporal clusters rarely overlap (recoverable by construction).
REGIME = dict(n=0.85, horizon=60000.0, mu=0.002, eps=0.35, c=1.7)
SEEDS = 12


def adjusted_rand(a, b):
    """Adjusted Rand Index between two labelings (numpy-only; no scikit-learn dependency)."""
    a = np.unique(np.asarray(a), return_inverse=True)[1]
    b = np.unique(np.asarray(b), return_inverse=True)[1]
    cont = np.zeros((a.max() + 1, b.max() + 1), dtype=np.int64)
    np.add.at(cont, (a, b), 1)
    comb2 = lambda x: x * (x - 1) // 2
    sc = comb2(cont).sum()
    sa = comb2(cont.sum(axis=1)).sum()
    sb = comb2(cont.sum(axis=0)).sum()
    total = comb2(a.size)
    expected = sa * sb / total if total else 0.0
    maxidx = (sa + sb) / 2.0
    return 1.0 if maxidx == expected else float((sc - expected) / (maxidx - expected))


def recover_tau_q(rng, regime=REGIME, seeds=SEEDS, grid=None):
    """Mean ARI(timing-only #3 membership, tree root_id) per k over `seeds` separable streams; argmax k
    is the result-blind TAU_Q_K. Returns per_k_ari, best_k, cleared (vs spec.RECOVERY_THRESHOLD)."""
    grid = spec.TAU_Q_GRID if grid is None else grid
    ss = np.random.SeedSequence(int(rng.integers(0, 2**32 - 1))).spawn(seeds)
    per_k = {k: [] for k in grid}
    for s in ss:
        r = np.random.default_rng(s)
        t, ibu, root, _ = labeled_stream(regime["n"], regime["horizon"], regime["mu"],
                                         regime["eps"], regime["c"], r)
        if t.size < 200:
            continue
        for k in grid:
            lab = _avalanche_labels(t, bin_width(t, k))     # t already time-sorted
            per_k[k].append(adjusted_rand(lab, root))
    per_k_ari = {k: (float(np.mean(v)) if v else 0.0) for k, v in per_k.items()}
    best_k = max(per_k_ari, key=per_k_ari.get)
    return {"per_k_ari": per_k_ari, "best_k": best_k,
            "cleared": per_k_ari[best_k] >= spec.RECOVERY_THRESHOLD}
