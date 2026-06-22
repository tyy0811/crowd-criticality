# Joint-fit recovery control (two-regime, known truth n=0.5) — 2026-06-22 00:18:57
Same joint (eps,c)-grid x flexible linear μ(t) K=12 as the real-data joint fit.

## A short-mem + mild ramp (separated)  (true eps=1.6, c=0.5, ramp=2.0x, n_true=0.5; N=21454)  D_good≈0.0068
  eps     c      n̂          ll     D_KS
  0.2   0.5   1.239        7893   0.0490
  0.2   1.0   1.283        7610   0.0640
  0.3   0.5   1.091        8014   0.0401
  0.3   1.0   1.117        7727   0.0584
  0.5   0.5   0.877        8139   0.0287
  0.5   1.0   1.012        7889   0.0474
  0.8   0.5   0.689        8247   0.0181
  0.8   1.0   0.809        8031   0.0389
  1.2   0.5   0.572        8311   0.0087
  1.2   1.0   0.684        8159   0.0291
  1.6   0.5   0.504        8323   0.0037  <-max-ll
  1.6   1.0   0.613        8237   0.0212
- n̂ range across grid: 0.504 .. 1.283   (true 0.5)
- max-ll shape: eps=1.6, c=0.5 -> n̂=0.504
- => RECOVERED (max-ll near true shape & n̂≈n_true, no runaway)

## B long-mem + strong ramp (overlap, matched)  (true eps=0.3, c=0.5, ramp=8.0x, n_true=0.5; N=16370)  D_good≈0.0078
  eps     c      n̂          ll     D_KS
  0.2   0.5   0.656        2073   0.0094
  0.2   1.0   0.834        2061   0.0140
  0.3   0.5   0.480        2075   0.0081
  0.3   1.0   0.615        2065   0.0129
  0.5   0.5   0.331        2076   0.0064  <-max-ll
  0.5   1.0   0.433        2070   0.0115
  0.8   0.5   0.240        2075   0.0062
  0.8   1.0   0.323        2073   0.0092
  1.2   0.5   0.183        2070   0.0076
  1.2   1.0   0.253        2074   0.0070
  1.6   0.5   0.151        2065   0.0085
  1.6   1.0   0.214        2074   0.0061
- n̂ range across grid: 0.151 .. 0.834   (true 0.5)
- max-ll shape: eps=0.5, c=0.5 -> n̂=0.331
- => RIDGE (n̂ spans / runs to heavy-tail boundary, no interior pin)
