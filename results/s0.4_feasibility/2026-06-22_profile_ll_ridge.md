# Profile log-likelihood ridge over n — 2026-06-22 00:21:55
profile_ll(n) = max over (eps,c) of the n-fixed flexible-μ(t) fit. Shallow across n = non-identified; rising-to-boundary with argmax eps->0.1 = degeneracy runaway.

## ...3503937838  (N=18019, horizon=9.1h)
    n   Δprofile_ll  argmax eps     c
 0.15        -711.2         1.1   1.0
 0.30        -413.3         0.7   2.0
 0.45        -227.9         0.7   2.0
 0.60        -107.6         0.4   2.0
 0.75         -41.8         0.4   2.0
 0.90         -55.2         0.2   1.0
 1.05           0.0         0.2   2.0
- profile_ll span across n∈[0.30,0.90] = 371.5 units (has curvature -> some n info)
- profile max at n=1.05, eps=0.2 (BOUNDARY/runaway -> degeneracy, no interior sub-critical max)

## ...9630680686  (N=22089, horizon=20.0h)
    n   Δprofile_ll  argmax eps     c
 0.15       -2174.9         1.1   2.0
 0.30       -1063.8         1.1   2.0
 0.45        -445.0         0.7   2.0
 0.60        -193.4         0.4   2.0
 0.75           0.0         0.4   2.0
 0.90          -2.1         0.4   2.0
 1.05          -7.2         0.2   2.0
- profile_ll span across n∈[0.30,0.90] = 1063.8 units (has curvature -> some n info)
- profile max at n=0.75, eps=0.4 (interior)

## ...9076918150  (N=34830, horizon=12.3h)
    n   Δprofile_ll  argmax eps     c
 0.15       -1591.6         1.1   1.0
 0.30        -830.3         1.1   2.0
 0.45        -396.3         0.7   2.0
 0.60        -183.7         0.7   2.0
 0.75         -53.2         0.4   2.0
 0.90           0.0         0.4   2.0
 1.05         -86.2         0.2   1.0
- profile_ll span across n∈[0.30,0.90] = 830.3 units (has curvature -> some n info)
- profile max at n=0.90, eps=0.4 (interior)
