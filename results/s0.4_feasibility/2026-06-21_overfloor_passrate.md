# Over-floor pass-rate (fixed assumed shape eps=0.4, c=0.5) -- 2026-06-21 19:05:55

GoF gate (bootstrap B=199, p_flag=0.1) on every market >= 16000 events, gap-guarded.
Stream validity re-checked per market via unique transaction_hash (§4b).

        market       N   n_fit   D_obs  p_boot    verdict      stream
 ...3503937838   18019   0.772  0.0644  0.0050    FLAGGED  clean(1:1)
 ...9630680686   22089   0.770  0.0966  0.0050    FLAGGED  clean(1:1)
 ...9076918150   34830   0.876  0.0516  0.0050    FLAGGED  clean(1:1)

PASS RATE: 0/3 markets admit the assumed Lomax shape.

Reading:
- 0/N pass -> rejection is SYSTEMATIC -> the assumed fixed shape is inadequate -> build the (eps,c)
  fitter (option 1) and re-test H1 (some power-law fits) vs H2 (Lomax family wrong). Cross-review first.
- >=2/3 pass -> the first flag is IDIOSYNCRATIC -> handle that market specially; the spec's
  "too few pass" fitter trigger does NOT fire.
- All n_fit are vs the ASSUMED shape and untrustworthy where verdict=FLAGGED.
