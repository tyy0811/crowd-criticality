# Stage-1 power-law recovery — the qualified-G1 verdict

Per `DECISIONS.md` 2026-06-16 (qualified G1): does the within-bin-marginalizing estimator recover the
branching ratio `n` from 2 s block-time-quantized data in the PROJECT regime — power-law / long-memory,
near-critical — not just the exponential proxy?

**Criterion:** MCEM (on 2 s-quantized counts) must track the **full-data SOE-MLE on the true un-quantized
times** — NOT the planted value (unrecoverable near critical even with perfect data). `|diff|` = MCEM − ref.

**Components anchored before use:** generator (Ogata residuals KS p=0.99 + horizon-certified planted-n),
SOE kernel (mass exact, integral 0.4% sub-grid), SOE likelihood (tracks exact O(N²) MLE to ≤0.004 incl
near-critical), MCEM (init-robust). See `2026-06-16_powerlaw_components.md`.

## Result 1 — hard-corner-first (eps=0.4)

The near-critical × sharp-within-bin corner (where within-bin order matters most) runs FIRST; if it tracks,
the envelope is the whole space.

| config | N | ref | MCEM | \|diff\| | acc | ess |
|---|---:|---:|---:|---:|---:|---:|
| **HARD** n=0.9 × sharp c=0.2 (F(2s)=0.62) | 512 | 0.808 | 0.809 | **0.000** | 0.78 | 10.0 |
| **HARD** n=0.9 × sharp c=0.2 (F(2s)=0.62) | 615 | 0.890 | 0.903 | **0.013** | 0.77 | 5.2 |
| EASY n=0.6 × mild c=2.0 (F(2s)=0.24) | 671 | 0.404 | 0.407 | 0.002 | 0.98 | 10.0 |
| EASY n=0.6 × mild c=2.0 (F(2s)=0.24) | 663 | 0.644 | 0.631 | 0.013 | 0.98 | 10.0 |

Acceptance drops 0.98 → 0.77 at the sharp corner — within-bin order **is** constrained there — and MCEM
tracks anyway. The hard corner passes at adequate N (≈600).

## Result 2 — near-critical edge (n → 0.99, sharp c=0.2)

| n | N | ref | MCEM | \|diff\| | acc |
|---:|---:|---:|---:|---:|---:|
| 0.95 | 294 | 0.836 | 0.822 | 0.013 | 0.76 |
| 0.95 | 257 | 0.909 | 0.920 | 0.011 | 0.73 |
| 0.97 | 145 | 0.911 | 0.908 | 0.003 | 0.74 |
| 0.97 |  96 | 0.819 | 0.819 | 0.000 | 0.72 |
| 0.99 |  86 | 0.934 | 0.933 | 0.000 | 0.74 |
| 0.99 |  76 | 0.924 | 0.923 | 0.000 | 0.74 |

MCEM tracks the reference through n=0.99 — **but note the N column (76–294)** and that ref ≈ 0.92 at
planted 0.99 (see the event-count caveat below).

## Verdict — two axes, kept separate

**Granularity: CLEARED.** MCEM tracks the full-data MLE to ≤0.013 across the entire envelope, incl the hard
corner at adequate N. 2 s block-time quantization does not destroy `n̂` recoverability; the within-bin
marginalization adds no bias beyond the full-data estimator. The continuous-MLE `inf` was estimator
inadequacy, resolved. Discrimination holds at the full-data resolution (planted 0.6 → ~0.5; 0.95+ → ~0.9).

**Event-count: the tiny near-critical N is the S0.2 floor, not a granularity result.** Near critical the
realized N collapses to ~76–294 (heavy-tail truncation; the MCEM compute wall O(N²·M) blocks large-N
near-critical runs), so the reference ITSELF can't resolve 0.99 (ref ≈ 0.92). That is the event-count floor
— S0.2-pending from the start — and the granularity result (MCEM ≈ full-data) holds regardless, even at
N=76. The two axes are orthogonal; only granularity was this gate's question.

## Claimed / not claimed
- **Claimed:** 2 s quantization does not destroy `n̂` recoverability (power-law, near-critical); the binned
  within-bin-marginalizing MCEM recovers it. Source A viable on granularity. Kernel SHAPE (eps, c) known.
- **Not claimed:** near-critical recovery at adequate event count (S0.2); shape jointly fitted; real-data
  certification (real within-bin dynamics may differ — owed).
