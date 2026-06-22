# Profile-ll calibration on known-truth synthetics (n_true=0.5) — 2026-06-22 10:19:58
Same profile-over-n measure as the real-data ridge. Does a known-non-identified regime falsely peak high?

## A short-mem+mild ramp (separated -> expect peak~0.5)  (true eps=1.6, c=0.5, ramp=2.0x, n_true=0.5; N=21742)
    n   Δprofile_ll  argmax eps     c
 0.15        -724.8         1.1   0.5
 0.30        -294.7         1.1   0.5
 0.45         -60.0         1.1   0.5
 0.60           0.0         1.1   0.5
 0.75         -97.5         0.7   0.5
 0.90        -169.7         0.7   0.5
 1.05        -240.4         0.4   0.5
- profile PEAK at n=0.60 (true 0.5); argmax eps=1.1
- => peak near truth -> profile LOCATES n correctly

## B long-mem+strong ramp (overlap, matched -> KEY)  (true eps=0.3, c=0.5, ramp=8.0x, n_true=0.5; N=16426)
    n   Δprofile_ll  argmax eps     c
 0.15         -13.3         1.1   0.5
 0.30          -1.9         0.7   1.0
 0.45          -1.1         0.4   0.5
 0.60           0.0         0.2   0.5
 0.75          -1.0         0.2   0.5
 0.90          -7.2         0.1   0.5
 1.05          -2.7         0.1   0.5
- profile PEAK at n=0.60 (true 0.5); argmax eps=0.2
- => peak near truth -> profile LOCATES n correctly
