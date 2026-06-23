# Joint n↔eps↔μ(t) fit — stage 1 (best shape | flexible smooth μ(t)) — 2026-06-21 23:43:40
Grid eps=[0.2, 0.4, 0.7, 1.1] x c=[0.5, 1.0, 2.0], linear μ(t) K=12.

## ...3503937838  (N=18019, horizon=9.1h)  D_good≈0.0074
  eps     c      n̂     D_KS
  0.2   0.5   0.817   0.0361
  0.2   1.0   1.016   0.0254
  0.2   2.0   1.130   0.0115  <-best
  0.4   0.5   0.488   0.0374
  0.4   1.0   0.641   0.0313
  0.4   2.0   0.798   0.0208
  0.7   0.5   0.314   0.0320
  0.7   1.0   0.442   0.0337
  0.7   2.0   0.584   0.0254
  1.1   0.5   0.215   0.0272
  1.1   1.0   0.318   0.0303
  1.1   2.0   0.446   0.0285
- BEST shape: eps=0.2, c=2.0 -> n̂=1.130, D=0.0115 (1.5x good-fit)
- GOOD FIT reachable -> a fitting (shape, μ(t)) EXISTS; STAGE 2: is n̂ pinned at this shape?

## ...9630680686  (N=22089, horizon=20.0h)  D_good≈0.0067
  eps     c      n̂     D_KS
  0.2   0.5   0.891   0.0641
  0.2   1.0   1.041   0.0493
  0.2   2.0   1.134   0.0295  <-best
  0.4   0.5   0.582   0.0710
  0.4   1.0   0.698   0.0619
  0.4   2.0   0.822   0.0473
  0.7   0.5   0.426   0.0712
  0.7   1.0   0.525   0.0667
  0.7   2.0   0.632   0.0573
  1.1   0.5   0.332   0.0671
  1.1   1.0   0.420   0.0660
  1.1   2.0   0.519   0.0614
- BEST shape: eps=0.2, c=2.0 -> n̂=1.134, D=0.0295 (4.4x good-fit)
- NO shape reaches good-fit even with flexible smooth μ(t) -> leans LOCKED (deep model problem / genuine non-identification surviving free shape)

## ...9076918150  (N=34830, horizon=12.3h)  D_good≈0.0054
  eps     c      n̂     D_KS
  0.2   0.5   0.937   0.0250
  0.2   1.0   1.091   0.0140
  0.2   2.0   1.179   0.0042  <-best
  0.4   0.5   0.589   0.0299
  0.4   1.0   0.733   0.0211
  0.4   2.0   0.885   0.0130
  0.7   0.5   0.413   0.0322
  0.7   1.0   0.534   0.0253
  0.7   2.0   0.664   0.0172
  1.1   0.5   0.306   0.0317
  1.1   1.0   0.414   0.0271
  1.1   2.0   0.533   0.0209
- BEST shape: eps=0.2, c=2.0 -> n̂=1.179, D=0.0042 (0.8x good-fit)
- GOOD FIT reachable -> a fitting (shape, μ(t)) EXISTS; STAGE 2: is n̂ pinned at this shape?
