"""The parrot-null rig: instantiate the coupled CRIT reference + the collapse parrot, verify the null is
real (two positive-control gates), and read the five-column instrument-discovery table off both. The
prototype artifact test is a NULL-CONFIRMATION: a collapsed null is all size-1 avalanches, so the τ-arm
reads 'no power law' by construction. See docs/superpowers/specs/2026-06-25-parrot-null-design.md."""
from __future__ import annotations

import numpy as np

from critaudit.powerlaw.csn import fit_powerlaw
from critaudit.scaling.crackling import exponents


def read_tau_arm(av, *, rng, n_boot):
    """The τ/crackling arm with a degenerate-avalanche guard. A collapsed null has all size-1 avalanches;
    powerlaw.Fit on constant data is degenerate, so short-circuit to 'no power law' (passes=False,
    tau=nan, p_boot=nan). Otherwise fit and reuse the fit's xmin for the size exponent (one xmin search).
    Returns (passes, tau, p_boot)."""
    sizes = np.asarray(av.sizes)
    if sizes.size == 0 or int(sizes.max()) < 2:
        return (False, float("nan"), float("nan"))
    pl = fit_powerlaw(sizes, rng=rng, n_boot=n_boot)
    tau, _alpha, _inv = exponents(av, xmin_size=pl.xmin)
    return (bool(pl.passes), float(tau), float(pl.p_boot))
