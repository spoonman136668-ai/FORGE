# G85 final-regression workflow repair — 2026-10-31

The original native ARM64 GPT-2 benchmark and immutable result are unchanged. The first final-regression run exposed two verifier-path mismatches: Linux exercised the deep-history G61 atlas path and reported G61_DIRTY_CHECKOUT; Windows failed its broad diff-check stage. Neither result indicates failure of the actual ARM64 experiment, whose engineering and exact-output correctness passed.

The exact-receipt workflow now uses the established depth-2 FORGE checkout contract, allowing the separate deep-history G61 lane to retain its own authority, and validates every unchanged G70 subtree/blob explicitly. Broad diff-check was removed because the regression already enforces exact source, prereg, result digest and immutable baseline identities.

G85 remains TRANSFER_FAIL; the frozen original numeric result is unchanged. This trigger exists only to retry the exact-receipt Linux/Windows regression and does not alter measurements, thresholds or scientific interpretation.