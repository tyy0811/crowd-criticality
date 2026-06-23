# MAGNITUDE probe — does migration EXTENT discriminate? — 2026-06-22 23:31:12

**PRE-REGISTERED RULE (frozen before any real-market peak; result-blind, finding 8):**
- plant genuine n=0.9 (conservative anti-circular anchor, NOT the suspect 0.75 fit), N matched down, 80 seeds; n-grid extended to 2.0 (no 1.20 wall).
- pool genuine-FALSE-migration peaks across regimes -> G; n* = 90th pctile of G.
- per real market: RESTORED if real peak > n*; GRADED if median(G) < peak <= n*; ABSENT if <= median.
- N=1 real obs/market -> at most 'real peak sits in the tail of G', a graded per-market statement.
- CEILING CHECK: if most of G sits at 2.00 the grid still walls -> extend further (flagged).

## Specificity (firmed CI) + genuine-false peaks, plant n=0.90

### 3503937838 (market N=18019, swing=7.7x; cal OK)
- false-migration 12/80 = 0.150; Wilson95 CI [0.088, 0.244]; specificity [0.756, 0.912]
- genuine-false peaks: [1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05]

### 9630680686 (market N=22089, swing=9.5x; cal **N-MISMATCH**)
- false-migration 4/80 = 0.050; Wilson95 CI [0.020, 0.122]; specificity [0.878, 0.980]
- genuine-false peaks: [1.05, 1.05, 1.05, 1.05]

### 9076918150 (market N=34830, swing=11.7x; cal OK)
- false-migration 7/80 = 0.087; Wilson95 CI [0.043, 0.170]; specificity [0.830, 0.957]
- genuine-false peaks: [1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05]

## Genuine-false-migration peak distribution G (pooled, n=0.90)
- N migrating seeds pooled = 23; median=1.05; n*(90th pctile)=1.05; fraction at ceiling 2.00 = 0.00
- CEILING CHECK: OK — genuine-false NOT piled at ceiling
- peaks: [1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05]

## Real markets on the extended grid — pre-registered rule applied

     market real peak@.02  pctile in G    verdict
 3503937838          1.20         100%   RESTORED
 9630680686          1.20         100%   RESTORED
 9076918150          0.90           0%     absent

Read: 'RESTORED' = the real market's migration is more extreme than 90% of genuine-false
migrations, so magnitude separates it where the binary did not (graded, N=1 real obs).
If real peaks AND G both pile at the 2.00 ceiling, magnitude cannot separate — extend further.