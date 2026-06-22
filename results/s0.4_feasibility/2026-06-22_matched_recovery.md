# Matched recovery control — plant each market's own fit, recover the planted n? — 2026-06-22 11:13:29
Read RECOVERY + profile SHAPE, not raw span (span scales with N). Event count + ramp matched.

## …9630680686 (plant n=0.75)  (planted N=21021, ramp=9.5x, n_true=0.75)
    n   Δprofile_ll  argmax eps     c
 0.15        -653.7         1.1   1.0
 0.30        -251.2         1.1   2.0
 0.45         -80.6         0.7   2.0
 0.60         -51.1         0.4   2.0
 0.75           0.0         0.4   2.0  <-peak
 0.90         -33.6         0.2   1.0
 1.05         -38.8         0.2   1.0
- profile PEAK at n=0.75 (planted 0.75); shape: interior peak; span 654 units
- => RECOVERED planted n -> real interior peaks are REAL, identification HOLDS

## …9076918150 (plant n=0.90)  (planted N=27643, ramp=11.7x, n_true=0.9)
    n   Δprofile_ll  argmax eps     c
 0.15        -825.3         1.1   1.0
 0.30        -378.7         1.1   2.0
 0.45        -172.3         0.7   2.0
 0.60         -46.4         0.7   2.0
 0.75         -33.0         0.4   2.0
 0.90           0.0         0.4   2.0  <-peak
 1.05         -26.2         0.2   1.0
- profile PEAK at n=0.90 (planted 0.9); shape: interior peak; span 825 units
- => RECOVERED planted n -> real interior peaks are REAL, identification HOLDS
