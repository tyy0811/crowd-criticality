"""Real-data granularity certification driver: goodness-of-fit GATES the granularity verdict.

Per market: fit the full-timing (mu, n) with the assumed power-law kernel; test the shape via the
time-rescaling KS statistic, calibrated by a parametric bootstrap (estimated-parameter KS is
anticonservative, and KS power falls with N -- both bias toward PASSING a misfit, the one direction a
shape gate must not fail). Only on a strongly-supported fit (p_boot >= p_flag) is the granularity diff
emitted; a wrong shape biases full and binned the same way, so a small diff under misfit is false
comfort -> flag, don't certify. High p_flag = stringent = flag-readily.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import numpy as np
from scipy.stats import kstest

from critaudit.hawkes.binned import PowerLawKernel, fit_full, certify_granularity, GranularityCert
from critaudit.generators import powerlaw_hawkes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # so `from b_reader import` resolves
from b_reader import read_markets                               # outside pytest's conftest (real run)


def _ks_stat(times, mu, n, kernel):
    """KS (statistic, p-value) of the time-rescaled inter-event intervals vs Exp(1); both from ONE
    rescaling+kstest. 0 stat = perfect fit. Returns (nan, nan) if too few intervals (<2)."""
    d = np.diff(powerlaw_hawkes.rescaled_times(np.sort(times), mu, n, kernel.eps, kernel.c))
    if d.size < 2:
        return np.nan, np.nan
    r = kstest(d, "expon")
    return float(r.statistic), float(r.pvalue)


@dataclass
class GofResult:
    stat: float          # observed KS statistic
    p_plain: float       # plain-KS p-value -- DIAGNOSTIC ONLY (anticonservative)
    p_boot: float        # parametric-bootstrap-calibrated p-value -- THE GATE
    b_eff: int           # effective bootstrap replicates (degenerate fits dropped)
    passed: bool         # p_boot >= p_flag


def goodness_of_fit(times, mu, n, kernel, rng, *, B=199, p_flag=0.10):
    """Bootstrap-calibrated GoF. Simulate from the fitted (n, mu, eps, c), refit, build the KS-stat
    null; p_boot = (1 + #{D_b >= D_obs}) / (1 + b_eff). passed iff p_boot >= p_flag.

    Returns p_boot = nan (caller routes -> inconclusive) when the verdict cannot be trusted: a
    degenerate observed stat (d_obs nan), or fewer effective replicates than can even reach p_flag
    (b_eff < ceil(1/p_flag), where the smallest achievable p_boot is already >= p_flag, so a flag is
    impossible). A near-critical fit whose bootstrap replicate explodes past max_events is dropped, not
    propagated -- exactly the regime the gate targets must not crash the capture."""
    times = np.sort(np.asarray(times, float))
    horizon = float(times[-1])
    d_obs, p_plain = _ks_stat(times, mu, n, kernel)
    if not np.isfinite(d_obs):
        return GofResult(stat=d_obs, p_plain=p_plain, p_boot=np.nan, b_eff=0, passed=False)
    min_b_eff = int(np.ceil(1.0 / p_flag))
    ge, b_eff = 0, 0
    for _ in range(B):
        try:
            tb = powerlaw_hawkes.simulate(n, horizon, mu, kernel.eps, kernel.c, rng)
        except RuntimeError:                       # event explosion (near-critical fit) -> drop replicate
            continue
        if tb.size < 10:
            continue
        mu_b, n_b = fit_full(tb, float(tb[-1]), kernel)
        d_b, _ = _ks_stat(tb, mu_b, n_b, kernel)
        if not np.isfinite(d_b):
            continue
        b_eff += 1
        if d_b >= d_obs:
            ge += 1
    p_boot = (1 + ge) / (1 + b_eff) if b_eff >= min_b_eff else np.nan
    passed = bool(np.isfinite(p_boot) and p_boot >= p_flag)
    return GofResult(stat=d_obs, p_plain=p_plain, p_boot=p_boot, b_eff=b_eff, passed=passed)


@dataclass
class MarketVerdict:
    asset_id: str
    n_events: int
    status: str                       # insufficient_events | inconclusive | flagged_shape_misfit | certified
    gof: "GofResult | None"
    cert: "GranularityCert | None"
    mu_full: "float | None"
    n_full: "float | None"


def certify_market(market, grid, kernel, rng, *, min_events, B=199, p_flag=0.10, **mcem_kw):
    """Goodness-of-fit GATES the granularity verdict. kernel: a PowerLawKernel (required by the GoF)."""
    if not isinstance(kernel, PowerLawKernel):
        raise TypeError("certify_market requires a PowerLawKernel (the GoF is power-law-specific)")
    if market.n_events < min_events or market.horizon <= 0:
        return MarketVerdict(market.asset_id, market.n_events, "insufficient_events",
                             None, None, None, None)
    mu_full, n_full = fit_full(market.times, market.horizon, kernel)
    gof = goodness_of_fit(market.times, mu_full, n_full, kernel, rng, B=B, p_flag=p_flag)
    if not np.isfinite(gof.p_boot):
        return MarketVerdict(market.asset_id, market.n_events, "inconclusive",
                             gof, None, mu_full, n_full)
    if not gof.passed:
        return MarketVerdict(market.asset_id, market.n_events, "flagged_shape_misfit",
                             gof, None, mu_full, n_full)
    cert = certify_granularity(market.times, grid, market.horizon, kernel, rng, n_full=n_full, **mcem_kw)
    return MarketVerdict(market.asset_id, market.n_events, "certified",
                         gof, cert, mu_full, n_full)


def _spawn_market_rngs(rng, markets):
    """One child rng per market, keyed by asset_id rank, so a market's bootstrap is independent of
    capture order and of how many rng draws other markets consumed (reproducible per asset)."""
    spawned = rng.spawn(len(markets))
    children = [None] * len(markets)
    for rank, i in enumerate(sorted(range(len(markets)), key=lambda j: markets[j].asset_id)):
        children[i] = spawned[rank]
    return children


def certify_capture(path, grid, kernel, rng, *, min_events, B=199, p_flag=0.10,
                    event_unit="fill", **mcem_kw):
    """Read a B capture and certify/flag every market. Returns a list of MarketVerdict. Each market
    gets an asset-keyed child rng so verdicts do not depend on capture order (or other markets)."""
    markets = read_markets(path, event_unit=event_unit)
    return [certify_market(m, grid, kernel, r, min_events=min_events, B=B, p_flag=p_flag, **mcem_kw)
            for m, r in zip(markets, _spawn_market_rngs(rng, markets))]
