"""Deterministic $0 CPU embedding realization (sub-inc-2 design 2026-07-17 §4).

sentence-transformers is imported LAZILY (the lazy-OASIS idiom of oasis_adapter): importing this
module for the pure pipeline never pulls torch, so the CI fast path stays torch-free — only the
@slow tier and the drivers call embed_texts.

Determinism levers (all frozen in llm_parrot_spec): CPU only (never MPS), float32, L2-normalized,
single torch thread, and STREAM-ORDER batch composition — texts are encoded in explicit
consecutive chunks of EMBED_BATCH_SIZE, so which texts share a forward pass is pinned by stream
position regardless of the library's internal length-sorting (batch composition changes fp sums).
Empty strings embed under the same uniform rule (special-tokens-only sequence) — disclosed, not
special-cased. Downstream, every cosine is rounded to COSINE_DECIMALS before any comparison.
"""
from __future__ import annotations
import numpy as np
from critaudit.sim.controls import llm_parrot_spec as lps

_MODEL_CACHE = {}


def _load_model(spec):
    """Load the PINNED revision, fail-closed: no fallback to an unpinned snapshot. Cached per
    (model_id, revision) so a driver embedding several windows loads once."""
    key = (spec.EMBED_MODEL_ID, spec.EMBED_REVISION)
    if key not in _MODEL_CACHE:
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(spec.EMBED_TORCH_THREADS)
        model = SentenceTransformer(spec.EMBED_MODEL_ID, revision=spec.EMBED_REVISION,
                                    device=spec.EMBED_DEVICE)
        if model.max_seq_length != spec.EMBED_MAX_SEQ_LENGTH:
            raise ValueError(
                f"pinned model max_seq_length {model.max_seq_length} != recorded "
                f"EMBED_MAX_SEQ_LENGTH {spec.EMBED_MAX_SEQ_LENGTH} — substrate drift")
        _MODEL_CACHE[key] = model
    return _MODEL_CACHE[key]


def embed_texts(texts, *, spec=lps):
    """Embed `texts` (sequence of str) -> (n, EMBED_DIM) float32, L2-normalized, in input order.
    FAIL-CLOSED on an empty input or a shape/norm surprise (a wrong-field or wrong-model bug must
    surface loudly, never as a silently odd marginal)."""
    texts = list(texts)
    if not texts:
        raise ValueError("embed_texts: empty input — nothing to embed (fail-closed)")
    model = _load_model(spec)
    chunks = []
    for start in range(0, len(texts), spec.EMBED_BATCH_SIZE):     # stream-order batch composition
        chunk = texts[start:start + spec.EMBED_BATCH_SIZE]
        chunks.append(model.encode(chunk, batch_size=spec.EMBED_BATCH_SIZE,
                                   convert_to_numpy=True,
                                   normalize_embeddings=spec.EMBED_NORMALIZE,
                                   show_progress_bar=False))
    E = np.vstack(chunks).astype(np.float32)
    if E.shape != (len(texts), spec.EMBED_DIM):
        raise ValueError(f"embedding shape {E.shape} != ({len(texts)}, {spec.EMBED_DIM})")
    norms = np.linalg.norm(E, axis=1)
    if not np.all(np.isfinite(E)) or not np.allclose(norms, 1.0, atol=1e-3):
        raise ValueError("embeddings not finite/unit-norm — normalization or model drift")
    return E
