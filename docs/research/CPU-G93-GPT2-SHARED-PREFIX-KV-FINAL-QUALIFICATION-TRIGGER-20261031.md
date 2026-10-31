# G93 final immutable receipt qualification — 2026-10-31

Original-model workflow #41224266651 completed successfully. Artifact #13050794668 was recovered and inspected. ZIP SHA-256: `4c89a0885c1c7968c6c367e16557e9aa102203bfdf8ebc52490324a28fccee79`; original result JSON SHA-256: `fe444db05eececa485c6aab29ddefdb9aafc58d61f99a3d187945dc4ef6cb482`; original environment SHA-256: `f5c3a48687dda8c6dd84af7bb1f8a23bbda26985e5fa18fc550605acd24410ee`.

The compact receipt and pinned environment are preserved in this branch.

Frozen result: **engineering PASS, correctness PASS, SHARED_PREFIX_KV_PASS**. Across a twelve-request identical-prefix cohort, median speedup was 2.328643× after charging one prefix prefill per cohort and independent per-request cache copies. Worst paired amortized request speedup was 2.108166×; p95 amortized latency ratio 0.473939; CPU ratio 0.428423; sampled RSS ratio 1.026151. All 96 full responses and 768 generated tokens matched exactly. The maximum first-token logit difference (1.0681e-4) is preserved as a floating-point-order sensitivity; greedy first token remained identical for every question.

This final workflow verifies immutable receipt/source identities, focused G93 tests, FORGE isolation/FSA, F139 custody and Linux/Windows final Go tests/race/vet/build. It does not rerun inference or claim general traffic benefits. Scientific acceptance remains NOT_GRANTED; promotion remains false.
