import numpy as np
import pytest
from reconstruct import fill_value, reconstruct


def _fill(block_time, usdc_units, share_units, usdc_is_maker=True):
    """Build one decoded OrderFilled under the documented encoding (USDC asset id '0',
    6 decimals on both legs). usdc_units/share_units are human units; convert to raw."""
    usdc_raw, share_raw = int(usdc_units * 1e6), int(share_units * 1e6)
    if usdc_is_maker:
        return {"block_time": block_time, "makerAssetId": "0", "takerAssetId": "7",
                "makerAmountFilled": usdc_raw, "takerAmountFilled": share_raw}
    return {"block_time": block_time, "makerAssetId": "7", "takerAssetId": "0",
            "makerAmountFilled": share_raw, "takerAmountFilled": usdc_raw}


def test_fill_value_decimals_and_price():
    # 60 USDC for 100 shares -> price 0.60, notional 60
    usdc, shares, price = fill_value(_fill(1000, 60.0, 100.0))
    assert usdc == pytest.approx(60.0)
    assert shares == pytest.approx(100.0)
    assert price == pytest.approx(0.60)


def test_fill_value_handles_usdc_on_either_leg():
    a = fill_value(_fill(1000, 30.0, 50.0, usdc_is_maker=True))
    b = fill_value(_fill(1000, 30.0, 50.0, usdc_is_maker=False))
    assert a == pytest.approx(b)  # (30, 50, 0.6) either way


def test_fill_value_rejects_non_usdc_pair():
    with pytest.raises(ValueError):
        fill_value({"block_time": 1, "makerAssetId": "7", "takerAssetId": "9",
                    "makerAmountFilled": 1, "takerAmountFilled": 1})


def test_reconstruct_notional_and_reconciliation():
    fills = [_fill(1000, 60.0, 100.0), _fill(1002, 40.0, 50.0), _fill(1010, 100.0, 200.0)]
    r = reconstruct(fills, reported_volume=200.0, grid=2.0)
    assert r.notional == pytest.approx(200.0)          # 60 + 40 + 100
    assert r.reconciliation_ratio == pytest.approx(1.0)  # 200 / 200
    assert r.n_events == 3


def test_reconstruct_times_relative_and_horizon():
    fills = [_fill(1000, 1.0, 2.0), _fill(1006, 1.0, 2.0)]
    r = reconstruct(fills, reported_volume=2.0, grid=2.0)
    assert r.times[0] == 0.0
    assert r.horizon == pytest.approx(6.0)
    assert r.marks.shape == (2, 2)  # (size, price) per event — EventStream-shaped, not imported


def test_reconstruct_tie_fraction_after_quantization():
    # three trades within one 2 s block (t=1000,1001) + one later -> ties after flooring
    fills = [_fill(1000, 1.0, 2.0), _fill(1001, 1.0, 2.0), _fill(1010, 1.0, 2.0)]
    r = reconstruct(fills, reported_volume=3.0, grid=2.0)
    assert r.tie_fraction == pytest.approx(0.5)  # diffs after floor: [0, >0] -> 1 of 2
