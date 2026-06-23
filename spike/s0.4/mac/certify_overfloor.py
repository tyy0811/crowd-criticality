#!/usr/bin/env python3
"""Option 2: fixed-shape GoF on the OTHER over-floor markets -> the PASS-RATE the spec's fitter
trigger needs ("a fitter earns its cost only if too few markets pass"). N=1 cannot answer that; this
establishes systematic-vs-idiosyncratic before any fitter is built. No new estimator code -- existing
GoF machinery on more markets. Stream-validity (unique transaction_hash) is re-checked per market.

The smallest over-floor market (...3503937838) already FLAGGED (2026-06-21_first_realdata_gof.md); this
runs the rest. Writes a combined pass-rate table.
"""
import json
import pathlib
import sys
import time

SPIKE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPIKE))
import numpy as np
from b_reader import read_markets
from critaudit.hawkes.binned import PowerLawKernel, fit_full
from realdata_cert import goodness_of_fit

OUT = "/Users/zenith/b_capture/ws_capture.jsonl"
RESULTS = SPIKE.parent.parent / "results" / "s0.4_feasibility"
EPS, C = 0.4, 0.5
FLOOR, B, P_FLAG, SLEEP_GAP_S = 16000, 199, 0.10, 60.0
DONE_TAIL = "3503937838"               # already flagged; cite, don't rerun
k = PowerLawKernel(eps=EPS, c=C)


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def stream_unique(asset_id):
    """§4b self-check: are this market's transaction_hashes 1:1 (clean) on the raw capture?"""
    hs = []
    for line in open(OUT):
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)["msg"]
        except Exception:
            continue
        if m.get("event_type") == "last_trade_price" and m.get("asset_id") == asset_id:
            hs.append(m.get("transaction_hash"))
    return len(set(hs)) == len(hs) and None not in hs, len(hs)


mk = read_markets(OUT, sleep_gap_s=SLEEP_GAP_S)
over = sorted((m for m in mk if m.n_events >= FLOOR), key=lambda m: m.n_events)
todo = [m for m in over if not m.asset_id.endswith(DONE_TAIL)]
log(f"{len(over)} markets over floor; running GoF on {len(todo)} (the smallest already flagged)")

rows = [("...%s" % DONE_TAIL, 18019, 0.7722, 0.0644, 0.0050, "FLAGGED", "clean(1:1)")]
for i, m in enumerate(todo):
    clean, nh = stream_unique(m.asset_id)
    mu, n = fit_full(m.times, m.horizon, k)
    log(f"[{i+1}/{len(todo)}] ...{m.asset_id[-10:]} N={m.n_events} n={n:.3f} "
        f"stream={'clean' if clean else 'DIRTY'} -> GoF B={B} (~tens of min)")
    t0 = time.time()
    gof = goodness_of_fit(m.times, mu, n, k, np.random.default_rng(100 + i), B=B, p_flag=P_FLAG)
    verdict = ("inconclusive" if not np.isfinite(gof.p_boot)
               else "PASSED" if gof.passed else "FLAGGED")
    log(f"   -> {verdict}  D_obs={gof.stat:.4f} p_boot={gof.p_boot:.4f} b_eff={gof.b_eff} "
        f"({(time.time()-t0)/60:.1f} min)")
    rows.append((f"...{m.asset_id[-10:]}", m.n_events, round(n, 4), round(gof.stat, 4),
                 round(gof.p_boot, 4), verdict, "clean(1:1)" if clean else "DIRTY"))

passed = sum(1 for r in rows if r[5] == "PASSED")
hdr = f"{'market':>14} {'N':>7} {'n_fit':>7} {'D_obs':>7} {'p_boot':>7} {'verdict':>10} {'stream':>11}"
table = "\n".join(f"{a:>14} {b:>7} {c:>7.3f} {d:>7.4f} {e:>7.4f} {f:>10} {g:>11}" for a, b, c, d, e, f, g in rows)
summary = f"""# Over-floor pass-rate (fixed assumed shape eps={EPS}, c={C}) -- {time.strftime('%Y-%m-%d %H:%M:%S')}

GoF gate (bootstrap B={B}, p_flag={P_FLAG}) on every market >= {FLOOR} events, gap-guarded.
Stream validity re-checked per market via unique transaction_hash (§4b).

{hdr}
{table}

PASS RATE: {passed}/{len(rows)} markets admit the assumed Lomax shape.

Reading:
- 0/N pass -> rejection is SYSTEMATIC -> the assumed fixed shape is inadequate -> build the (eps,c)
  fitter (option 1) and re-test H1 (some power-law fits) vs H2 (Lomax family wrong). Cross-review first.
- >=2/3 pass -> the first flag is IDIOSYNCRATIC -> handle that market specially; the spec's
  "too few pass" fitter trigger does NOT fire.
- All n_fit are vs the ASSUMED shape and untrustworthy where verdict=FLAGGED.
"""
outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_overfloor_passrate.md"
outp.write_text(summary)
log(f"PASS RATE {passed}/{len(rows)} -> {outp}")
print("\n" + summary)
