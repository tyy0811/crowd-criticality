# FINER-GRID / continuous-peak check — is the 1.05-vs-1.20 separation real or quantization? — 2026-06-23 00:51:07

**PRE-REGISTERED RULE (frozen before results, finding 8):** separation HOLDS iff (a) genuine fine migration-peaks' 95th pctile <= 1.125 (genuine stays clearly below the real 1.20) AND (b) each migrating real market has profile argmax >= 1.175 and ll(argmax)-ll(1.05) >= 10.0 (a steep max, not a flat 1.05-1.20 ridge). Else COLLAPSES -> resolution-floor + the binary population claim.
n-grid fine through 1.0-1.3 (step 0.025); plant genuine n=0.90, 40 seeds, per-market N-matched; eps-stability checked on the real markets.

## Genuine (n=0.90) fine-grid migration peaks — TIGHT cluster or SPREAD?
- 3503937838 (N=18019): 11 migrated, fine peaks [1.05, 1.05, 1.075, 1.075, 1.075, 1.075, 1.075, 1.1, 1.1, 1.1, 1.125]
- 9630680686 (N=22089): 7 migrated, fine peaks [1.075, 1.075, 1.075, 1.075, 1.1, 1.1, 1.125]
- 9076918150 (N=34830): 10 migrated, fine peaks [1.075, 1.075, 1.075, 1.075, 1.1, 1.1, 1.1, 1.1, 1.1, 1.125]
- pooled genuine fine peaks N=28; median=1.075; 95th pctile=1.125; max=1.125 -> SPREADS toward real

## Real markets — continuous profile (steep max at 1.20 or flat ridge?) + eps-stability
### 3503937838  argmax_n=1.125 (eps-fine grid: 1.125 -> endpoint STABLE)
- ll(argmax)-ll(1.05) = 13.3 units -> STEEP (1.20 clearly favored)
- profile Δll vs max (n: Δll): [(0.9, -68.5), (0.95, -49.7), (1.0, -29.4), (1.025, -20.8), (1.05, -13.3), (1.075, -6.9), (1.1, -2.2), (1.125, 0.0), (1.15, -1.1), (1.175, -5.4), (1.2, -12.9), (1.25, -38.8), (1.3, -81.5), (1.45, -56.2)]

### 9630680686  argmax_n=1.125 (eps-fine grid: 1.125 -> endpoint STABLE)
- ll(argmax)-ll(1.05) = 27.3 units -> STEEP (1.20 clearly favored)
- profile Δll vs max (n: Δll): [(0.9, -22.1), (0.95, -60.4), (1.0, -65.4), (1.025, -44.7), (1.05, -27.3), (1.075, -13.5), (1.1, -4.2), (1.125, 0.0), (1.15, -0.7), (1.175, -6.6), (1.2, -17.8), (1.25, -55.8), (1.3, -116.9), (1.45, -169.5)]

### 9076918150  argmax_n=0.900 (eps-fine grid: 0.900 -> endpoint STABLE)
- ll(argmax)-ll(1.05) = 86.2 units -> STEEP (1.20 clearly favored)
- profile Δll vs max (n: Δll): [(0.9, 0.0), (0.95, -11.3), (1.0, -41.9), (1.025, -65.8), (1.05, -86.2), (1.075, -81.1), (1.1, -80.5), (1.125, -84.3), (1.15, -92.0), (1.175, -89.5), (1.2, -90.7), (1.25, -105.3), (1.3, -147.4), (1.45, -237.4)]

## PRE-REGISTERED VERDICT
- genuine 95th pctile 1.125 <= 1.125? **True**
- every migrating real market a steep max (argmax>=1.175, sharp>=10.0)? **False** (failing: ['3503937838', '9630680686'])
- => SEPARATION **COLLAPSES — back to resolution-floor + the binary population claim**

Bankable regardless (grid-independent): the BINARY population claim — P(this migrate/not pattern | all 3 smooth-genuine) ~ 2% (depends on WHICH migrate, not how far). Non-stationarity inflation untouched. Even if separation holds, the per-market verdict is 'not SMOOTH-genuine', NOT 'degenerate' — bursty-genuine gives the same signature; that is the bursty chapter.