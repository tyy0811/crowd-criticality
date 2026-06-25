import numpy as np
import pytest
from critaudit.types import AvalancheSet
from critaudit.experiments.parrot_null import read_tau_arm


def test_read_tau_arm_degenerate_is_no_power_law():
    # collapsed null: every avalanche size 1 -> no power law admissible, no powerlaw.Fit call
    av = AvalancheSet(sizes=np.ones(500, np.int64), durations=np.ones(500, np.int64))
    passes, tau, p_boot = read_tau_arm(av, rng=np.random.default_rng(0), n_boot=20)
    assert passes is False
    assert np.isnan(tau) and np.isnan(p_boot)


def test_read_tau_arm_nondegenerate_returns_finite_tau():
    # a varied size distribution -> the fit runs and returns a finite tau and a bool verdict.
    # durations must VARY too: read_tau_arm -> exponents() also fits durations, and a constant
    # durations array crashes powerlaw's xmin search ("no data points in range"). Real avalanche
    # sets always have generation-depth durations that grow with size (a size>1 tree has depth>=2);
    # only the size-1 collapsed case has constant durations, and that path is the degenerate guard.
    rng = np.random.default_rng(0)
    sizes = (rng.zipf(2.0, size=3000)).astype(np.int64)   # heavy-tailed integer sizes, max >> 1
    durations = np.maximum(1, np.ceil(np.log2(sizes + 1)).astype(np.int64))  # depth ~ log(size)
    av = AvalancheSet(sizes=sizes, durations=durations)
    passes, tau, p_boot = read_tau_arm(av, rng=np.random.default_rng(1), n_boot=20)
    assert isinstance(passes, bool)
    assert np.isfinite(tau)
