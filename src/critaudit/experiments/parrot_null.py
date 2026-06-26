"""The parrot-null rig: instantiate the coupled CRIT reference + the collapse parrot, verify the null is
real (two positive-control gates, fail-closed), and read the five-column instrument-discovery table off
both. The prototype artifact test is a NULL-CONFIRMATION: a collapsed null is all size-1 avalanches, so
the τ-arm reads 'no power law' by construction. See docs/superpowers/specs/2026-06-25-parrot-null-design.md."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from critaudit.powerlaw.csn import fit_powerlaw
from critaudit.scaling.crackling import exponents
from critaudit.sim.controls.deffuant import simulate_labeled
from critaudit.sim.controls.parrot import simulate_parrot
from critaudit.sim.controls.anchors import n_tree, n_struct, burstiness, fano_profile
from critaudit.cascades.extract import post_reply_tree
from critaudit.hawkes.gate import certify_near_critical
from critaudit.sim.controls import parrot_spec as ps


@dataclass
class ArmRead:
    """The full τ/crackling arm (frozen design §7 col 1): the size power law (passes/τ/p_boot) PLUS the
    duration exponent α, the curvature 1/σνz, and the crackling Δ-residual = (α−1)/(τ−1) − 1/σνz (the
    scaling-collapse consistency check). All nan on a degenerate avalanche set; the crackling trio is nan
    when durations are degenerate even if τ is defined (the size verdict still stands)."""
    passes: bool
    tau: float
    p_boot: float
    alpha: float
    inv_snz: float
    delta: float


def read_tau_arm(av, *, rng, n_boot) -> ArmRead:
    """The τ/crackling arm with degenerate-avalanche guards. powerlaw.Fit on constant data is degenerate
    (raises 'no data points in defined range'), so short-circuit to 'no power law' BEFORE any fit:
      • < 2 distinct SIZES  -> the whole arm is undefined (collapsed null is all size-1; also catches
        constant-size>=2, which `sizes.max() < 2` missed and which crashes powerlaw) -> all-nan, passes=False.
      • < 2 distinct DURATIONS -> the size power law still holds, but the duration fit (inside exponents())
        would crash; return the τ verdict with the crackling trio (α, 1/σνz, Δ) = nan.
    τ is read from pl.exponent (the size exponent; bit-identical to exponents(av, xmin_size=pl.xmin)[0], so
    the xmin search runs ONCE); α/1/σνz come from exponents() reusing that xmin; Δ is the crackling residual."""
    sizes = np.asarray(av.sizes)
    durations = np.asarray(av.durations)
    nan = float("nan")
    if sizes.size == 0 or np.unique(sizes).size < 2:
        return ArmRead(passes=False, tau=nan, p_boot=nan, alpha=nan, inv_snz=nan, delta=nan)
    pl = fit_powerlaw(sizes, rng=rng, n_boot=n_boot)
    tau = float(pl.exponent)
    if np.unique(durations).size < 2:
        return ArmRead(passes=bool(pl.passes), tau=tau, p_boot=float(pl.p_boot),
                       alpha=nan, inv_snz=nan, delta=nan)
    _tau, alpha, inv_snz = exponents(av, xmin_size=pl.xmin)
    delta = (alpha - 1.0) / (tau - 1.0) - inv_snz if (np.isfinite(inv_snz) and tau != 1.0) else nan
    return ArmRead(passes=bool(pl.passes), tau=tau, p_boot=float(pl.p_boot),
                   alpha=float(alpha), inv_snz=float(inv_snz), delta=float(delta))


@dataclass
class ColumnRead:
    tau_passes: bool          # col 1: τ/crackling arm — null-confirmation, NOT a survival criterion
    tau: float
    p_boot: float
    alpha: float              # col 1 (crackling): duration exponent α ...
    inv_snz: float            # ... curvature 1/σνz ...
    crackling_delta: float    # ... scaling-collapse residual Δ = (α−1)/(τ−1) − 1/σνz (nan if undefined)
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
    tripwire_ok: bool         # parrot.successes == 0 (enforced UPSTREAM by simulate_parrot's fail-close)
    struct_ok: bool           # n_struct(parrot) == 0.0 (enforced at the rig, below)


def _read_columns(run, *, n_match, rng, n_boot, horizon, window_sizes):
    if run.times.size == 0:
        raise ValueError("parrot-null _read_columns needs >= 1 event (mis-sized substrate?)")  # cf. run_pipeline
    av = post_reply_tree(run.times, run.root_id, run.parent_idx)
    arm = read_tau_arm(av, rng=rng, n_boot=n_boot)
    m = min(int(n_match), run.times.size)
    t = run.times[:m]
    g = certify_near_critical(t, float(t[-1]))     # N-matched, mirrors shakedown.run_pipeline
    return ColumnRead(tau_passes=arm.passes, tau=arm.tau, p_boot=arm.p_boot,
                      alpha=arm.alpha, inv_snz=arm.inv_snz, crackling_delta=arm.delta,
                      n_struct=n_struct(av), burstiness=burstiness(run.times),
                      fano=fano_profile(run.times, horizon, window_sizes),
                      n_emit=n_tree(run),
                      gate_peak=g.peak, gate_migrated=g.migrated, gate_identified=g.identified)


def run_parrot_null(*, seed=ps.SEED, N=ps.N_AGENTS, k_reach=ps.K_REACH, mu_step=ps.MU_STEP,
                    kernel_eps=ps.KERNEL_EPS, c=ps.KERNEL_C, horizon=ps.HORIZON,
                    mu_news=ps.REFERENCE_MU_NEWS, reference_eps=ps.REFERENCE_EPS,
                    n_match=ps.N_MATCH, n_boot=ps.N_BOOT, window_sizes=ps.FANO_WINDOW_SIZES):
    """Instantiate the coupled CRIT reference + the collapse parrot on the SAME substrate, verify the null
    is real (the §6 positive control), and read the five-column table off both. Independent RNG streams for
    the two generators and the two CSN bootstraps (SeedSequence.spawn). FAIL-CLOSED: the positive control
    (tripwire successes==0 AND structural n_struct==0) is ENFORCED here — a deviation blocks interpretation
    of all candidate columns (design §6), so the rig RAISES rather than returning manufactured diagnostics.
    The tripwire is also enforced upstream by simulate_parrot; the structural gate is the rig's own check
    (it catches an edge-injecting bypass that leaves successes==0 — the case the tripwire cannot see)."""
    rc, rp, rcsn_c, rcsn_p = (np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(4))
    coupled_run = simulate_labeled(reference_eps, horizon, mu_news, N=N, k_reach=k_reach,
                                   mu_step=mu_step, kernel_eps=kernel_eps, c=c, rng=rc)
    parrot_run = simulate_parrot(horizon, mu_news, N=N, k_reach=k_reach, mu_step=mu_step,
                                 kernel_eps=kernel_eps, c=c, rng=rp)
    coupled = _read_columns(coupled_run, n_match=n_match, rng=rcsn_c, n_boot=n_boot,
                            horizon=horizon, window_sizes=window_sizes)
    parrot = _read_columns(parrot_run, n_match=n_match, rng=rcsn_p, n_boot=n_boot,
                           horizon=horizon, window_sizes=window_sizes)
    tripwire_ok = (parrot_run.successes == 0)
    struct_ok = (parrot.n_struct == 0.0)
    if not (tripwire_ok and struct_ok):
        raise AssertionError(f"parrot positive control failed: successes={parrot_run.successes}, "
                             f"n_struct={parrot.n_struct} (expected 0 / 0.0 — residual coupling or an "
                             f"edge-injecting bypass; blocks interpretation of all columns, design §6)")
    return ParrotNullResult(coupled=coupled, parrot=parrot, tripwire_ok=tripwire_ok, struct_ok=struct_ok)
