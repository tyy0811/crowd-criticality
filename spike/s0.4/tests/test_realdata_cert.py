import numpy as np
import pytest

from critaudit.hawkes.binned import PowerLawKernel, fit_full
from critaudit.generators import powerlaw_hawkes
from critaudit.generators.hawkes_sim import simulate as exp_simulate

from realdata_cert import goodness_of_fit, certify_market, MarketVerdict
from b_reader import MarketEvents

# small B keeps tests fast; production uses B=199. Seeds are fixed for determinism: under H0 the
# calibrated p is ~U(0,1), so ~p_flag of seeds would flag matched data -- the chosen seeds do not.


def test_gof_passes_on_matched_powerlaw():
    k = PowerLawKernel(eps=0.4, c=0.5)
    t = powerlaw_hawkes.simulate(0.6, 1500.0, 0.4, 0.4, 0.5, np.random.default_rng(0))
    mu, n = fit_full(t, float(t[-1]), k)
    gof = goodness_of_fit(t, mu, n, k, np.random.default_rng(1), B=39, p_flag=0.10)
    assert gof.passed and gof.p_boot > 0.10
    assert gof.b_eff > 30


def test_gof_flags_gross_exp_kernel_misfit():
    # data is EXP-kernel Hawkes; we assume a power-law shape -> strong misfit -> flag.
    k = PowerLawKernel(eps=0.3, c=1.0)
    es = exp_simulate(0.6, 1500.0, mu=0.4, beta=1.0, rng=np.random.default_rng(2))
    mu, n = fit_full(es.times, float(es.times[-1]), k)
    gof = goodness_of_fit(es.times, mu, n, k, np.random.default_rng(3), B=39, p_flag=0.10)
    assert not gof.passed and gof.p_boot < 0.10


@pytest.mark.slow   # ~14 min (N~1.6e4 x B refits). Skippable for iteration (-m "not slow") but
                    # MANDATORY before declaring done: this is the test proving the gate catches an
                    # n̂-biasing misfit, not merely a gross wrong-family mismatch.
def test_gof_flags_subtle_wrong_exponent():
    # data is Lomax with eps_true=0.2; we assume eps=0.7 -> a MODERATE shape error that biases n̂ HARD
    # and DOWNWARD (n: 0.6 -> ~0.23): a self-exciting market read as strongly subcritical = false-
    # NEGATIVE criticality. This is DISTINCT FROM and OPPOSITE TO the granularity bias (which pushes n̂
    # UP toward critical); both directions are live, the gate + min_events floor must guard both, and a
    # market carrying both can have them partly CANCEL -- a plausible n̂ that is right for the wrong
    # reasons. The misfit is KS-INVISIBLE at low N: measured 2026-06-18, its KS plateaus ~0.01 while a
    # correctly-specified fit's KS -> 0 (~1/sqrt(N)), so the flag is a POWER question, not absorption.
    # H=2000 (N~1.5e3) does NOT flag (p_boot~0.9); H=20000 (N~1.6e4) flags robustly (p_boot 0.025-0.05
    # across data seeds 4/14/24). ~1.6e4 is a FLOOR for THIS (large) error; subtler n̂-biasing errors
    # need more, so the real GoF-power floor is >=1.6e4 -- the sharp number behind the spec's min_events.
    k_assumed = PowerLawKernel(eps=0.7, c=0.5)
    t = powerlaw_hawkes.simulate(0.6, 20000.0, 0.4, 0.2, 0.5, np.random.default_rng(4))
    mu, n = fit_full(t, float(t[-1]), k_assumed)
    gof = goodness_of_fit(t, mu, n, k_assumed, np.random.default_rng(5), B=39, p_flag=0.10)
    assert not gof.passed


def _market(asset, times):
    times = np.sort(np.asarray(times, float))
    return MarketEvents(asset_id=asset, times=times, horizon=float(times[-1]),
                        t0_unix_s=0.0, n_events=int(times.size),
                        max_ms_multiplicity=1, n_tied_events=0, n_dup_price_consecutive=0)


def test_certify_market_insufficient_events_skips_gof():
    k = PowerLawKernel(eps=0.4, c=0.5)
    m = _market("A", [0.0, 1.0, 2.0])
    v = certify_market(m, 2.0, k, np.random.default_rng(0), min_events=100, B=39)
    assert v.status == "insufficient_events" and v.gof is None and v.cert is None


def test_certify_market_certifies_matched_market():
    k = PowerLawKernel(eps=0.4, c=0.5)
    t = powerlaw_hawkes.simulate(0.6, 1500.0, 0.4, 0.4, 0.5, np.random.default_rng(0))
    v = certify_market(_market("A", t), 2.0, k, np.random.default_rng(1),
                       min_events=200, B=39, p_flag=0.10, em_iters=8, sweeps=2)
    assert v.status == "certified"
    assert v.cert is not None and abs(v.n_full - 0.6) < 0.15
    assert abs(v.cert.diff) < 0.15            # 2 s loses little n̂ on matched dynamics


def test_certify_market_flags_gross_misfit():
    k = PowerLawKernel(eps=0.3, c=1.0)
    es = exp_simulate(0.6, 1500.0, mu=0.4, beta=1.0, rng=np.random.default_rng(2))
    v = certify_market(_market("A", es.times), 2.0, k, np.random.default_rng(3),
                       min_events=200, B=39, p_flag=0.10)
    assert v.status == "flagged_shape_misfit" and v.cert is None and v.gof is not None


import json
from realdata_cert import certify_capture


def _write_synth_capture(path, t0_ms, market_times, inject_ties=0):
    """Wrap generator output (seconds from 0) into B-JSONL with a large Unix-ms t0. Optionally inject
    `inject_ties` extra fills at the first market's first timestamp (same-ms multi-fill mimic)."""
    lines = []
    for asset, times in market_times.items():
        ms = [t0_ms + int(round(t * 1000)) for t in np.sort(times)]
        if inject_ties and asset == next(iter(market_times)):
            ms = [ms[0]] * inject_ties + ms
        for m in sorted(ms):
            lines.append(json.dumps({"recv_ts": m / 1000.0,
                                     "msg": {"event_type": "last_trade_price", "asset_id": asset,
                                             "timestamp": str(m), "price": "0.5"}}))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def test_certify_capture_end_to_end_recovers_n(tmp_path):
    # Reference-reproduction through the REAL plumbing: generator -> B-JSONL (large t0 + injected
    # same-ms ties) -> reader -> driver. The dense matched market certifies and recovers n; the sparse
    # market is gated out; ties flow through the zero-base + fit_full path intact.
    rng = np.random.default_rng(0)
    dense = powerlaw_hawkes.simulate(0.6, 1500.0, 0.4, 0.4, 0.5, rng)
    sparse = powerlaw_hawkes.simulate(0.5, 60.0, 0.2, 0.4, 0.5, rng)
    path = str(tmp_path / "cap.jsonl")
    _write_synth_capture(path, 1_700_000_000_000, {"DENSE": dense, "SPARSE": sparse}, inject_ties=20)

    k = PowerLawKernel(eps=0.4, c=0.5)
    verdicts = {v.asset_id: v for v in
                certify_capture(path, 2.0, k, np.random.default_rng(1),
                                min_events=200, B=39, p_flag=0.10, em_iters=8, sweeps=2)}

    assert verdicts["SPARSE"].status == "insufficient_events"
    assert verdicts["DENSE"].status == "certified"
    assert abs(verdicts["DENSE"].n_full - 0.6) < 0.15
    assert np.isfinite(verdicts["DENSE"].cert.diff)   # ties survived the full path, fit stayed finite
