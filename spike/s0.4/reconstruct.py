"""Reconstruct a trade-arrival point process from decoded Polymarket CTF-Exchange fills.

Pure logic only — the decoded rows arrive from Dune (Task 5, offsite). The output MIRRORS
critaudit.types.EventStream's (times, horizon, marks) shape but does NOT import it: the
firewall holds, and real block-time data has same-block ties that EventStream's
strictly-increasing invariant would (correctly) reject — itself the granularity signal.

CONFIRM-AT-RUNTIME (spec §10): USDC is asset id "0"; both legs carry 6 decimals; price =
usdc/shares; the SQL supplies one-side (de-duplicated) fills. The Task-4 expected_ratio
absorbs any residual double-count.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from granularity import quantize_to_grid, tie_fraction

USDC_ASSET_ID = "0"   # CTF-Exchange collateral leg — CONFIRM at runtime
DECIMALS = 6          # USDC and (assumed) conditional-token units — CONFIRM at runtime


@dataclass
class Reconstruction:
    times: np.ndarray            # seconds, relative to the first fill (EventStream-shaped)
    horizon: float
    marks: np.ndarray            # (n, 2) -> (size_shares, price); EventStream's reserved slot
    notional: float              # sum of USDC traded
    reconciliation_ratio: float  # notional / reported_volume
    tie_fraction: float          # same-block ties after flooring to `grid`
    n_events: int


def fill_value(fill: dict) -> tuple[float, float, float]:
    """(usdc, shares, price) for one decoded OrderFilled under the documented encoding."""
    if str(fill["makerAssetId"]) == USDC_ASSET_ID:
        usdc_raw, share_raw = fill["makerAmountFilled"], fill["takerAmountFilled"]
    elif str(fill["takerAssetId"]) == USDC_ASSET_ID:
        usdc_raw, share_raw = fill["takerAmountFilled"], fill["makerAmountFilled"]
    else:
        raise ValueError(f"neither leg is USDC (asset id {USDC_ASSET_ID!r}): {fill!r}")
    usdc = usdc_raw / 10**DECIMALS
    shares = share_raw / 10**DECIMALS
    price = usdc / shares if shares else float("nan")
    return usdc, shares, price


def reconstruct(fills: list[dict], reported_volume: float, grid: float = 2.0) -> Reconstruction:
    """Decoded fills -> trade-arrival point process + notional + reconciliation + ties."""
    fills = sorted(fills, key=lambda f: f["block_time"])
    raw_t = np.array([f["block_time"] for f in fills], dtype=float)
    usdc_shares_price = np.array([fill_value(f) for f in fills], dtype=float)  # (n, 3)
    notional = float(usdc_shares_price[:, 0].sum())
    t0 = raw_t[0] if raw_t.size else 0.0
    times = raw_t - t0
    horizon = float(times[-1]) if times.size else 0.0
    marks = usdc_shares_price[:, 1:3]  # (size_shares, price)
    return Reconstruction(
        times=times, horizon=horizon, marks=marks, notional=notional,
        reconciliation_ratio=(notional / reported_volume if reported_volume else float("nan")),
        tie_fraction=tie_fraction(quantize_to_grid(times, grid)),
        n_events=len(fills),
    )
