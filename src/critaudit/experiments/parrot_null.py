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


from dataclasses import dataclass

from critaudit.sim.controls.deffuant import simulate_labeled
from critaudit.sim.controls.parrot import simulate_parrot
from critaudit.sim.controls.anchors import n_tree, n_struct, burstiness, fano_profile
from critaudit.cascades.extract import post_reply_tree
from critaudit.hawkes.gate import certify_near_critical
from critaudit.sim.controls import parrot_spec as ps


@dataclass
class ColumnRead:
    tau_passes: bool          # col 1: τ/crackling arm — null-confirmation, NOT a survival criterion
    tau: float
    p_boot: float
    n_struct: float           # col 2: reconstructed structural branching (structural positive control)
    burstiness: float         # col 3: model-free temporal clustering ...
    fano: np.ndarray          # ... scale-resolved
    n_emit: float             # col 5: generative emission-time analog (== n_gen in Deffuant)
    gate_peak: float          # col 4: BLIND-REFERENCE n̂ — NO candidate status, never tuned
    gate_migrated: float
    gate_identified: bool


@dataclass
class ParrotNullResult:
    coupled: ColumnRead       # the CRIT reference (contrast baseline)
    parrot: ColumnRead        # the collapse null
    tripwire_ok: bool         # parrot.successes == 0
    struct_ok: bool           # n_struct(parrot) == 0.0


def _read_columns(run, *, n_match, rng, n_boot, horizon, window_sizes):
    av = post_reply_tree(run.times, run.root_id, run.parent_idx)
    tau_passes, tau, p_boot = read_tau_arm(av, rng=rng, n_boot=n_boot)
    m = min(int(n_match), run.times.size)
    t = run.times[:m]
    g = certify_near_critical(t, float(t[-1]))     # N-matched, mirrors shakedown.run_pipeline
    return ColumnRead(tau_passes=tau_passes, tau=tau, p_boot=p_boot,
                      n_struct=n_struct(av), burstiness=burstiness(run.times),
                      fano=fano_profile(run.times, horizon, window_sizes),
                      n_emit=n_tree(run),
                      gate_peak=g.peak, gate_migrated=g.migrated, gate_identified=g.identified)


def run_parrot_null(*, seed=ps.SEED, N=ps.N_AGENTS, k_reach=ps.K_REACH, mu_step=ps.MU_STEP,
                    kernel_eps=ps.KERNEL_EPS, c=ps.KERNEL_C, horizon=ps.HORIZON,
                    mu_news=ps.REFERENCE_MU_NEWS, reference_eps=ps.REFERENCE_EPS,
                    n_match=ps.N_MATCH, n_boot=ps.N_BOOT, window_sizes=ps.FANO_WINDOW_SIZES):
    """Instantiate the coupled CRIT reference + the collapse parrot on the SAME substrate, verify the
    null is real (tripwire + structural gate), and read the five-column table off both. Independent RNG
    streams for the two generators and the two CSN bootstraps (SeedSequence.spawn)."""
    rc, rp, rcsn_c, rcsn_p = (np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(4))
    coupled_run = simulate_labeled(reference_eps, horizon, mu_news, N=N, k_reach=k_reach,
                                   mu_step=mu_step, kernel_eps=kernel_eps, c=c, rng=rc)
    parrot_run = simulate_parrot(horizon, mu_news, N=N, k_reach=k_reach, mu_step=mu_step,
                                 kernel_eps=kernel_eps, c=c, rng=rp)
    coupled = _read_columns(coupled_run, n_match=n_match, rng=rcsn_c, n_boot=n_boot,
                            horizon=horizon, window_sizes=window_sizes)
    parrot = _read_columns(parrot_run, n_match=n_match, rng=rcsn_p, n_boot=n_boot,
                           horizon=horizon, window_sizes=window_sizes)
    return ParrotNullResult(coupled=coupled, parrot=parrot,
                            tripwire_ok=(parrot_run.successes == 0),
                            struct_ok=(parrot.n_struct == 0.0))
