# G94 immutable result qualification — 2026-10-31

Original-model workflow #41225515691 completed successfully. Artifact #13051053217 was recovered. ZIP SHA-256: `fb78e69b9b50eac27a1d14e39ede266e4b81e8fd04040c14a63ad75cb06b7757`; result JSON SHA-256: `1857899648f671c47e5ed7eae376fc790070354b4ccbbeb3e95f61ec10ab267b`; environment SHA-256: `d4d2023f7008a608427e35ac9f13ef40ba3941397cb1769d4670c6591029991c`.

The original evidence, compact receipt and environment copy are preserved in this branch.

Frozen outcome: **engineering PASS, correctness PASS, KV_COHORT_SCALE_PASS**. Cohort throughput speedups versus full-prompt recomputation were 1.390× (2), 1.808× (4), 2.005× (6), and 2.245× (12). Every prefix build and cache copy was included. All 240 responses and 1,920 generated tokens were exact. This verifies one repeated prefix only; multiple prefix keys and LRU eviction remain untested.

The receipt-only final workflow checks exact provenance, G94 tests, isolation/FSA, F139 custody, Go tests/race/vet/build on Linux and Windows. It does not rerun inference. Scientific acceptance remains NOT_GRANTED; promotion remains false.
