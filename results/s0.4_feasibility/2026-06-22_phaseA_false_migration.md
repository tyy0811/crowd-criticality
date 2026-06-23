# PHASE A (FROZEN) — false-migration rate of genuine near-critical under the gate — 2026-06-22 19:10:38
plant n=0.9 (near-critical), off-grid shape eps=0.35/c=1.7; ramp=swing-1 (#6); mu0 tuned to realized N; 8 seeds; gate frozen: identified iff |peak(eps0.02)-peak(eps0.4)|<0.15 AND peak<1.

p_migrate = fraction of GENUINE near-critical seeds the gate WRONGLY flags (migrated).

## regime 3503937838  (market N=18019, swing=7.7x, qr=5.5; calibrated synth realized N≈18563, swing≈7.8x, qr≈5.5; plant n=0.9)
seed  synthN synSwing  peak@0.4  peak@0.02 peak<1@.02    verdict
   0   20482     7.6x      0.90       0.90       0.90         OK
   1   19400     9.8x      0.90       0.90       0.90         OK
   2   19015     6.4x      0.90       0.90       0.90         OK
   3   18904     8.1x      0.90       0.90       0.90         OK
   4   19575     6.6x      0.90       0.90       0.90         OK
   5   19114    10.5x      0.90       1.05       0.90   MIGRATED
   6   18163    12.8x      0.90       0.90       0.90         OK
   7   18396    10.0x      0.90       0.90       0.90         OK
- **p_migrate(genuine near-critical @ N=18019, swing=7.7x) = 1/8 = 0.12**

## regime 9630680686  (market N=22089, swing=9.5x, qr=8.0; calibrated synth realized N≈25740, swing≈13.3x, qr≈6.4; plant n=0.9)
seed  synthN synSwing  peak@0.4  peak@0.02 peak<1@.02    verdict
   0   27868    11.9x      0.90       0.90       0.90         OK
   1   26457    13.2x      0.90       0.90       0.90         OK
   2   27488    10.8x      0.90       0.90       0.90         OK
   3   25692    11.6x      0.90       0.90       0.90         OK
   4   26896    12.3x      0.90       0.90       0.90         OK
   5   26074    12.1x      0.90       0.90       0.90         OK
   6   26019     7.9x      0.90       0.90       0.90         OK
   7   26493     8.1x      0.90       0.90       0.90         OK
- **p_migrate(genuine near-critical @ N=22089, swing=9.5x) = 0/8 = 0.00**

## regime 9076918150  (market N=34830, swing=11.7x, qr=10.1; calibrated synth realized N≈41218, swing≈13.2x, qr≈7.5; plant n=0.9)
seed  synthN synSwing  peak@0.4  peak@0.02 peak<1@.02    verdict
   0   42472    13.6x      0.90       0.90       0.90         OK
   1   41913    16.4x      0.90       0.90       0.90         OK
   2   42759    11.4x      0.90       0.90       0.90         OK
   3   39328    14.6x      0.90       0.90       0.90         OK
   4   40115    14.2x      0.90       0.90       0.90         OK
   5   42901    19.8x      0.90       0.90       0.90         OK
   6   42314    15.0x      0.90       0.90       0.90         OK
   7   42501    10.8x      0.90       0.90       0.90         OK
- **p_migrate(genuine near-critical @ N=34830, swing=11.7x) = 0/8 = 0.00**

## FROZEN baseline (read BEFORE Phase B)
A single real market's migration is interpretable only against p_migrate here:
  p_migrate LOW  (<= ~1/8) -> a real market that migrates is genuinely degenerate/mis-modelled.
  p_migrate HIGH (~half)   -> a single real migration is uninformative -> near-criticality
                              NOT RESOLVABLE at that N (resolution-floor reading).

  3503937838: p_migrate=0.12
  9630680686: p_migrate=0.00
  9076918150: p_migrate=0.00