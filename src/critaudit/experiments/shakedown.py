"""End-to-end shakedown runner: an AbmRun through the full criticality pipeline. The gate read is
N-matched to the first n_match events (apples-to-apples across plants at the gof-power floor); the
scaling/CSN arm consumes the full avalanche set; the gate-independent anchors ride alongside."""
from __future__ import annotations
from dataclasses import dataclass

import numpy as np

from critaudit.types import AvalancheSet
from critaudit.hawkes.gate import certify_near_critical, GateVerdict
from critaudit.cascades.extract import post_reply_tree
from critaudit.powerlaw.csn import fit_powerlaw, PowerLawFit
from critaudit.scaling.crackling import exponents
from critaudit.sim.controls.anchors import n_tree as _n_tree, chi as _chi


@dataclass
class ShakedownResult:
    gate: GateVerdict
    av: AvalancheSet
    pl: PowerLawFit
    tau: float
    alpha: float
    inv_snz: float
    n_tree: float
    chi: float
    n_events: int


def run_pipeline(run, *, n_match, csn_rng=None, n_boot=200):
    # n_boot is the CSN goodness-of-fit bootstrap depth; default 200 is the production/discrimination
    # value (Task 7 / real use). It is a BUDGET knob, not a result threshold (the frozen separation
    # criterion lives in spec.py): the discrimination cohort + @fast plumbing pass a small n_boot so they
    # do not pay the full 200-replicate bootstrap (~minutes/call on a large stream), since res.pl's p_boot
    # is never ASSERTED by any criterion — gate/n_tree/res.tau/chi are all independent of bootstrap depth.
    if run.times.size == 0:
        raise ValueError("run_pipeline needs >= 1 event (mis-sized plant?)")   # cf. anchors.n_tree
    m = min(int(n_match), run.times.size)
    t = run.times[:m]
    horizon = float(t[-1])
    gate = certify_near_critical(t, horizon)                       # μ(t) Hawkes gate (N-matched)
    av = post_reply_tree(run.times, run.root_id, run.parent_idx)   # scaling arm: full stream
    pl = fit_powerlaw(av.sizes, rng=csn_rng, n_boot=n_boot)
    # reuse pl's xmin for the size exponent so the (deterministic) xmin search runs ONCE, not twice
    # (res.tau == pl.exponent — both are the size power-law alpha); alpha/inv_snz use durations/curvature.
    tau, alpha, inv_snz = exponents(av, xmin_size=pl.xmin)
    return ShakedownResult(gate=gate, av=av, pl=pl, tau=tau, alpha=alpha, inv_snz=inv_snz,
                           n_tree=_n_tree(run), chi=_chi(run), n_events=m)
