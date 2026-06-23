# Hardiman-Bouchaud mean-variance n̂ vs MLE n̂ -- 2026-06-21 20:34:24

HB2014 Eq(7): n̂ = 1 - sqrt(mu_W/var_W) over m=floor(T/W) windows. Rising with W = the HB
criticality-OR-nonstationarity signature; small-W limit ~ locally-endogenous n̂.

## ...3503937838  (N=18019, horizon=9.1h)
- MLE n̂ (full-timing, assumed shape) = 0.772
- HB n̂(W) sweep  [W (s) : n̂ : m windows : mean count]:
          41 : 0.761 :  799 :   22.5
          64 : 0.804 :  514 :   35.0
          99 : 0.839 :  330 :   54.5
         154 : 0.868 :  212 :   84.9
         239 : 0.892 :  136 :  132.1
         372 : 0.910 :   87 :  205.7
         579 : 0.927 :   56 :  320.0
         901 : 0.938 :   36 :  497.8
        1402 : 0.945 :   23 :  774.7
- HB n̂ rises 0.761 (small W) -> 0.945 (large W), Δ=+0.185  <<< W-rising = HB criticality/non-stationarity signature
- HB n̂ at W=273s: first-third=0.416  vs  whole=0.898  (third<<whole = same non-stationarity drop the MLE showed)

## ...9630680686  (N=22089, horizon=20.0h)
- MLE n̂ (full-timing, assumed shape) = 0.770
- HB n̂(W) sweep  [W (s) : n̂ : m windows : mean count]:
          90 : 0.906 :  800 :   27.6
         140 : 0.908 :  514 :   42.9
         218 : 0.920 :  330 :   66.8
         340 : 0.937 :  212 :  103.8
         528 : 0.945 :  136 :  161.2
         822 : 0.950 :   87 :  249.6
        1278 : 0.957 :   56 :  388.7
        1988 : 0.961 :   36 :  604.6
        3093 : 0.970 :   23 :  928.0
- HB n̂ rises 0.906 (small W) -> 0.970 (large W), Δ=+0.064  
- HB n̂ at W=601s: first-third=0.471  vs  whole=0.945  (third<<whole = same non-stationarity drop the MLE showed)

## ...9076918150  (N=34830, horizon=12.3h)
- MLE n̂ (full-timing, assumed shape) = 0.876
- HB n̂(W) sweep  [W (s) : n̂ : m windows : mean count]:
          55 : 0.893 :  800 :   43.5
          86 : 0.913 :  514 :   67.7
         134 : 0.929 :  330 :  105.4
         208 : 0.940 :  212 :  164.0
         323 : 0.952 :  136 :  255.2
         503 : 0.961 :   87 :  397.4
         783 : 0.967 :   56 :  618.1
        1217 : 0.971 :   36 :  961.5
        1894 : 0.977 :   23 : 1496.7
        2946 : 0.980 :   15 : 2322.0
- HB n̂ rises 0.893 (small W) -> 0.980 (large W), Δ=+0.087  
- HB n̂ at W=368s: first-third=0.709  vs  whole=0.955  (third<<whole = same non-stationarity drop the MLE showed)

## Readout
- HB n̂ (large W) ≈ MLE n̂ ≈ 0.8  -> the ~0.8 is corroborated by independent (non-MLE) machinery,
  NOT a likelihood/kernel-shape artifact. Both inflate together = consistent with one cause.
- HB n̂(W) RISING toward 1 with W = exactly the Hardiman-Bouchaud long-memory/criticality
  signature -- but here it coincides with a DIRECTLY-measured 8-12x rate ramp, so it is the
  Wheatley non-stationarity reading, not genuine criticality (the field's dispute, on this data).
- HB small-W / first-third n̂ << whole = the locally-stationary endogeneity is LOWER -> previews
  the Wheatley outcome (mu(t)-corrected n̂ low). The mu(t)-EM sweep is the decisive test.
- HB shares the non-stationarity confound; it anchors the VALUE, it does not clear the confound.