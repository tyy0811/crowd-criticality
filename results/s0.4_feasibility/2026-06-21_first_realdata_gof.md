# First real GoF-gated certification -- 2026-06-21 13:28:19

market:        ...3503937838  (full asset_id 81043398291360463170235957547610256181022662944963722274721633505163503937838)
N (guarded):   18019
horizon:       32704 s  (9.1 h)
assumed shape: PowerLawKernel(eps=0.4, c=0.5)  | grid 2.0s
fit:           mu=0.1341  n=0.7722
GoF:           D_obs=0.0644  p_plain=0.000  p_boot=0.0050  b_eff=199/199
runtime:       52.8 min

VERDICT: FLAGGED shape misfit -> assumed Lomax shape rejected

Notes:
- p_boot is the bootstrap-CALIBRATED gate (p_plain is the anticonservative plain-KS diagnostic).
- n is provisional vs the ASSUMED shape; GoF tests whether that shape is admissible.
- Sleep-gap guard applied (recv_ts window), excluding the 2026-06-20 lid-sleep period.
- Granularity diff (n_binned vs n_full) NOT computed: certify_granularity MCEM is O(N^2*M)/sweep,
  intractable at N>=16k (the GoF-power floor). Resolve as a separate estimator-scaling task.

## Confound check (2026-06-21) -- multi-fill ties RULED OUT
The spec flagged that same-ms multi-fill bursts can masquerade as shape misfit at fill granularity.
Measured for this market: max_ms_multiplicity=2, n_tied=18 (0.1% of events), and fill-vs-match is a
no-op (N 18019->18010, n identical 0.772, D_obs 0.0644->0.0647). So the flag is NOT an event-unit
artifact -- the shape misfit is real and robust to fill/match aggregation. (dup_price=15128 = 84%
consecutive same-price fills confirms genuine per-fill emission, redline-2.)

## Interpretation -- what this does and does NOT establish
ESTABLISHED (robust): the FIXED assumed Lomax shape (eps=0.4, c=0.5) is decisively rejected for this
real near-critical market. D_obs=0.064 is ~8x the ~1/sqrt(N)~0.0075 a correct fit would give -- a
SIZEABLE misfit, not a marginal eps tweak. Bootstrap-confirmed (p_boot=0.005), gap-guarded, tie-robust.
The gate works on real data: it flags, it does not silently certify.

NOT established: (a) whether a FITTED (eps,c) -- or any power-law shape -- would pass; the GoF holds the
shape fixed, so "wrong eps" and "Lomax is the wrong family" both produce this flag. (b) representativeness
(N=1 market; the other 2 over-floor markets are untested).

DECISION THIS FORCES (the spec's trigger -- "a fitter earns its cost only if too few markets pass"):
  H1 wrong-assumed-shape, power-law-family-OK  -> a free (eps,c) fit passes -> BUILD THE SHAPE FITTER.
  H2 Lomax-family-wrong-for-real-data          -> even best-fit (eps,c) flags -> deeper model rethink.
Distinguishing H1/H2 = fit (eps,c) freely on this market + re-GoF. That is the sharpened divergent
unknown, and the next real step. n=0.772 here is UNTRUSTWORTHY (fit under a rejected shape).
