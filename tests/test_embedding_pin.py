"""@slow embedding-pin tests (sub-inc-2 T4): the pinned model loads, embeds deterministically on
CPU, and the NEWS_POOL checksum anchors cross-run determinism. Slow tier because it imports torch
and runs the real model; skipped wholesale where the optional [embed] extra is absent."""
import hashlib

import numpy as np
import pytest

st = pytest.importorskip("sentence_transformers", reason="optional [embed] extra not installed")

from critaudit.sim.harness import harness_spec as hs               # noqa: E402
from critaudit.sim.harness.embedding import embed_texts            # noqa: E402

# Banked determinism anchor (measured 2026-07-17 in the pinned substrate: ~/oasis_venv,
# sentence-transformers 3.0.0 / torch 2.2.2 / CPU / the frozen realization). An ENVIRONMENT
# anchor: a torch/sentence-transformers version change may legitimately move it — that is exactly
# the drift this test exists to surface loudly (re-bank consciously, never silently).
_NEWS_POOL_SHA256 = "08c6859dc6e0ebf9c566569cac05747fc74cbb14ab5e22ca2172e39e20472b88"


@pytest.mark.slow
def test_pinned_model_embeds_news_pool_deterministically():
    E1 = embed_texts(hs.NEWS_POOL)
    E2 = embed_texts(hs.NEWS_POOL)
    assert E1.shape == (len(hs.NEWS_POOL), 384) and E1.dtype == np.float32
    assert E1.tobytes() == E2.tobytes()                # bit-identical re-encode, same process
    assert np.allclose(np.linalg.norm(E1, axis=1), 1.0, atol=1e-3)
    assert hashlib.sha256(E1.tobytes()).hexdigest() == _NEWS_POOL_SHA256


@pytest.mark.slow
def test_empty_string_embeds_under_uniform_rule():
    # Reposts contribute "" to the authored pool (design §3/§7): the empty string embeds like any
    # text (special-tokens-only sequence) — finite, unit-norm, no special-casing.
    E = embed_texts([""])
    assert E.shape == (1, 384) and np.all(np.isfinite(E))
    assert np.isclose(np.linalg.norm(E), 1.0, atol=1e-3)


@pytest.mark.slow
def test_embed_texts_fail_closed_on_empty_input():
    with pytest.raises(ValueError, match="empty input"):
        embed_texts([])
