# Identifiability floor vs kernel MEMORY (planted n=0.85, ramp=10.0x) — 2026-06-22 13:23:27
Cell = peak-n; IDENTIFIED iff stays at planted 0.85; degenerate iff runs to 1.05/1.20.

 N_target | eps 0.1 | eps 0.2 | eps 0.3 | eps 0.4
    12000 | 0.85✓(N=3472) | 0.85✓(N=5844) | 0.60✓(N=8140) | 0.85✓(N=9826)
    20000 | 0.85✓(N=5683) | 0.85✓(N=9544) | 0.60✓(N=13205) | 0.85✓(N=16133)
    30000 | 0.85✓(N=8602) | 0.85✓(N=14350) | 1.20×(N=20218) | 0.85✓(N=24350)
    45000 | 0.85✓(N=12913) | 0.85✓(N=21758) | 1.20×(N=29503) | 0.85✓(N=35283)

## floor(eps): smallest N that IDENTIFIES
- eps=0.1 (tail heavy): floor ≈ 12000 events
- eps=0.2 (tail heavy): floor ≈ 12000 events
- eps=0.3 (tail lighter): floor ≈ 12000 events
- eps=0.4 (tail lighter): floor ≈ 12000 events

Read: if floor RISES into 22–45k as eps shrinks to 0.1–0.2, the real split is a MEMORY-dependent floor (markets 1,2 heavy-tail below floor; market 3 eps=0.4 above). If floor stays <~15k even at eps=0.1, the real degenerate markets are MIS-MODELLED, not floored.