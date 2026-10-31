# G84 final-regression workflow repair — 2026-10-31

The original Windows CPU GPT-2 benchmark and its evidence are unchanged. Previous final-regression attempts exposed inconsistent checkout assumptions and stopped before the complete integration suite could finish on both operating systems.

The exact-receipt workflow now follows the established FORGE source-regression pattern: depth-2 checkout, immutable G70 subtree/blob identity checks rather than requiring a deep Git ancestry object, and no broad whole-branch whitespace gate. The original preregistration, benchmark source/test, result JSON, SHA-256 sidecar, G70 model source trees, F139 custody/isolation tests and native Go regression remain mandatory.

Original result remains TRANSFER_FAIL with engineering/correctness PASS. This trigger only requests a new exact-receipt Linux/Windows source qualification; it does not alter result bytes, thresholds or scientific classification.