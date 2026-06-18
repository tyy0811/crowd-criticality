# Stage-1 power-law recovery — the qualified-G1 verdict

Per `DECISIONS.md` 2026-06-16 (qualified G1): the blocking gate was whether the within-bin-
marginalizing estimator recovers the branching ratio `n` from 2 s block-time-quantized data in the
PROJECT regime — power-law / long-memory, near-critical — not just the exponential proxy.

**Criterion (review):** MCEM (on 2 s-quantized counts) must track the **full-data SOE-MLE on the true
un-quantized times** — NOT the planted value, which is unrecoverable near critical even with perfect
data. Discrimination judged at the resolution the full timing itself achieves.

**All components anchored before use** (each on its own output): generator (Ogata residuals KS p=0.99
+ horizon-certified planted-n), SOE kernel (consumed functionals: mass exact, integral 0.4% sub-grid),
SOE likelihood (tracks exact O(N²) MLE to ≤0.004 across n incl near-critical), MCEM (init-robust on the
exponential de-risk). See `2026-06-16_powerlaw_components.md`, `validate_soe*.py`.

## Recovery envelope (eps=0.4; MCEM vs full-data SOE-MLE; |diff| = MCEM − reference)

| n | within-bin (c, F(2s)) | N | ref | MCEM | \|diff\| | acc |
|---:|---|---:|---:|---:|---:|---:|
| 0.6 | mild (c=2.0, 0.24) | 671 | 0.404 | 0.407 | 0.002 | 0.98 |
| 0.6 | mild (c=2.0, 0.24) | 663 | 0.644 | 0.631 | 0.013 | 0.98 |
| **0.9** | **sharp (c=0.2, 0.62)** | 512 | 0.808 | 0.809 | **0.000** | 0.78 |
| **0.9** | **sharp (c=0.2, 0.62)** | 615 | 0.890 | 0.903 | **0.013** | 0.77 |
| 0.95 | sharp (c=0.2, 0.62) | 294 | 0.836 | 0.822 | 0.013 | 0.76 |
| 0.95 | sharp (c=0.2, 0.62) | 257 | 0.909 | 0.920 | 0.011 | 0.73 |
| 0.97 | sharp (c=0.2, 0.62) | 145 | 0.911 | 0.908 | 0.003 | 0.74 |
| 0.99 | sharp (c=0.2, 0.62) | 86 | 0.934 | 0.933 | 0.000 | 0.74 |
| 0.99 | sharp (c=0.2, 0.62) | 76 | 0.924 | 0.923 | 0.000 | 0.74 |

Hard-corner-first: the near-critical × sharp-within-bin corner (where within-bin order matters most —
acceptance drops to ~0.73 vs ~0.98 mild) was run first; it passed, so the envelope is the whole space.

## Verdict — two axes, kept separate

**Granularity: CLEARED.** MCEM tracks the full-data MLE to ≤0.013 across the entire envelope, including
the hard corner at adequate N (≈600). **2 s block-time quantization is not a barrier to n̂ recovery** —
the within-bin marginalization adds no bias beyond the full-data estimator, even where within-bin order
is most constrained. The `inf` from the original continuous-MLE sweep was estimator inadequacy, fully
resolved. Discrimination holds at the full-data resolution (planted 0.6 → ~0.5; planted 0.95+ → ~0.9).

**Event-count: the tiny near-critical N is the S0.2 floor, not a granularity result.** The near-critical
configs collapsed to N≈76–294 (heavy-tail truncation + low μ; the MCEM compute wall O(N²·M) blocks
large-N near-critical runs), so the **reference itself** can't resolve 0.99 (ref ≈ 0.92 at planted 0.99).
That is the **event-count floor — S0.2-pending from the start** — and the granularity result (MCEM ≈
full-data) holds *regardless*, even at N=76. Granularity and event-count are orthogonal; only the former
was this gate's question.

## What is and isn't claimed
- **Claimed:** 2 s quantization does not destroy `n̂` recoverability in the power-law / near-critical
  regime; the binned within-bin-marginalizing MCEM is the estimator that recovers it. Source A is viable
  on the granularity axis. Kernel SHAPE (eps, c) known — the favorable case isolating n-recovery.
- **Not claimed:** near-critical recovery at adequate event count (that is S0.2's floor); recovery with
  the shape jointly fitted; real-data certification (real within-bin dynamics may differ — still owed).
