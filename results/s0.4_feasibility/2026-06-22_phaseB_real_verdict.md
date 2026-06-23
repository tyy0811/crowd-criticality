# PHASE B (VERDICT) — real over-floor markets through the frozen gate — 2026-06-22 23:14:21
Read each real market's migration against its regime's Phase-A p_migrate (the frozen baseline).

     market       N  swing  peak@0.4  peak@0.02 peak<1@.02    verdict  p_mig(genuine)
 3503937838   18019   7.7x      0.75       1.20       0.75   MIGRATED            nan
 9630680686   22089   9.5x      0.75       1.20       0.75   MIGRATED            nan
 9076918150   34830  11.7x      0.90       0.90       0.90         OK            nan

Interpretation rule (frozen): a real MIGRATED verdict is meaningful only where the genuine
p_migrate is low; where genuine p_migrate ~ 0.5 the real migration is single-realization noise
and the honest verdict is 'near-criticality not resolvable at this N'. peak<1@.02 separates a
finite-window artifact (interior subcritical max under the n<1 cap) from a genuine supercritical
mode (cap binds at the n-grid top).