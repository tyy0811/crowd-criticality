# Non-stationarity check (over-floor markets) -- 2026-06-21 19:37:55

Assumed shape eps=0.4, c=0.5; gap-guarded; K_RATE=8; synthetic seeds=3.
n_whole = fit_full n on full history; thirds = n on each 1/3; real_gap = n_whole - mean(thirds);
syn_gap = same gap on a STATIONARY simulate() at the fitted params (the pure edge effect).

## ...3503937838  (N=18019, horizon=9.1h, mu_full=0.134)
- rate/hr per 8-window: [480, 577, 922, 3384, 2446, 2240, 3688, 2127]
- rate SWING (max/min): 7.7x
- n_whole=0.772  halves=[0.744, 0.661]  thirds=[0.058, 0.638, 0.699]
- real_gap (whole - mean thirds) = +0.307   synthetic stationary edge-effect gap = +0.002
- => excess over edge effect = +0.305  <<< INFLATION (non-stationary)

## ...9630680686  (N=22089, horizon=20.0h, mu_full=0.075)
- rate/hr per 8-window: [281, 382, 466, 504, 937, 938, 2679, 2624]
- rate SWING (max/min): 9.5x
- n_whole=0.770  halves=[0.071, 0.812]  thirds=[0.049, 0.599, 0.794]
- real_gap (whole - mean thirds) = +0.289   synthetic stationary edge-effect gap = +0.001
- => excess over edge effect = +0.288  <<< INFLATION (non-stationary)

## ...9076918150  (N=34830, horizon=12.3h, mu_full=0.113)
- rate/hr per 8-window: [678, 768, 945, 1325, 1402, 3033, 6629, 7919]
- rate SWING (max/min): 11.7x
- n_whole=0.876  halves=[0.351, 0.888]  thirds=[0.169, 0.484, 0.855]
- real_gap (whole - mean thirds) = +0.374   synthetic stationary edge-effect gap = +0.002
- => excess over edge effect = +0.372  <<< INFLATION (non-stationary)

## Readout
- rate non-stationarity present (any swing >5x): True
- n̂ inflation beyond edge effect (any excess >0.08): True

- BOTH false -> stationary; the 0/3 rejection is about SHAPE; the (eps,c) fitter is the right
  next step; take the design doc to cross-review.
- EITHER true -> non-stationary; n̂ absorbs rate variation; the shape-fitter is the WRONG tool;
  fix = inhomogeneous mu(t)/windowed fits; reopen whether n̂ measures reflexivity at all.
- Either way: add non-stationarity to the fitter doc as a TESTED alternative (numbers in hand).