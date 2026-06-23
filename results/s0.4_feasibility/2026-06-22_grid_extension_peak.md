# Grid-extension peak migration — 2026-06-22 11:14:41
peak-n vs eps_min cutoff. STAYS PUT = interior max (identified); CLIMBS toward 1 = runaway.

## ...3503937838  (N=18019, horizon=9.1h)
 eps_min  peak-n  argmax eps  argmax c
     0.4    0.75         0.4       2.0
     0.2    1.20         0.2       2.0
     0.1    1.20         0.2       2.0
    0.05    1.20         0.2       2.0
    0.02    1.20         0.2       2.0
- peak-n: 0.75 (eps_min=0.4) -> 1.20 (eps_min=0.02); Δ=+0.45
- => CLIMBS toward/past 1 -> truncation artifact, runaway/degeneracy

## ...9630680686  (N=22089, horizon=20.0h)
 eps_min  peak-n  argmax eps  argmax c
     0.4    0.75         0.4       2.0
     0.2    1.20         0.2       2.0
     0.1    1.20         0.2       2.0
    0.05    1.20         0.2       2.0
    0.02    1.20         0.2       2.0
- peak-n: 0.75 (eps_min=0.4) -> 1.20 (eps_min=0.02); Δ=+0.45
- => CLIMBS toward/past 1 -> truncation artifact, runaway/degeneracy

## ...9076918150  (N=34830, horizon=12.3h)
 eps_min  peak-n  argmax eps  argmax c
     0.4    0.90         0.4       2.0
     0.2    0.90         0.4       2.0
     0.1    0.90         0.4       2.0
    0.05    0.90         0.4       2.0
    0.02    0.90         0.4       2.0
- peak-n: 0.90 (eps_min=0.4) -> 0.90 (eps_min=0.02); Δ=+0.00
- => STAYS PUT -> real interior maximum, identification HOLDS
