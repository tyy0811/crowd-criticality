from __future__ import annotations
import numpy as np


def pure_power_law(n_samples, rng, exponent=2.5):
    """Exact discrete power law P(s) proportional to s**-exponent, s>=1 — the Zipf /
    zeta distribution, drawn by inverse transform via numpy's `zipf`.

    This is the Gate-A.1 POSITIVE CONTROL. Unlike the critical Galton-Watson generator
    (whose avalanche sizes are Borel-Tanner — only ASYMPTOTICALLY s**-3/2, with a small
    non-universal bulk curvature), a Zipf draw is a STRICT power law, so it passes the
    Clauset CSN goodness-of-fit by construction. The Borel is the wrong object to demand a
    strict-power-law A.1 pass from; that role belongs here. (See DECISIONS.md 2026-06-16.)

    Default exponent is 2.5, NOT the critical 1.5: a clean s**-3/2 gets KS-selected
    xmin=1, so the Clauset GoF bootstrap (p_tail=1) regenerates a full heavy-tail sample
    and refits it every replicate — intractable at the harness N. The A.1 gate is
    exponent-agnostic (it tests power-law-ness, not the exponent), so a steeper, light-
    tailed exact power law is an equally valid positive control and is what the harness
    uses; 2.5 is also the exponent the CSN unit test already validates.

    Returns a 1-D int64 array of sizes (all >= 1)."""
    if exponent <= 1.0:
        raise ValueError("exponent must exceed 1 (zeta distribution requires a > 1)")
    return rng.zipf(exponent, size=n_samples).astype(np.int64)
