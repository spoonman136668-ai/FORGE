# G90 archived measurement receipt and final qualification — 2026-10-31

Original-model execution completed successfully in workflow #41217105263. Artifact #13049080046 was recovered and inspected. ZIP SHA-256: `ec1ad765aae41799aa1489795ab8a6259425fb4586037b9d313602fa7c9b6870`; original JSON SHA-256: `29f36fc348f0e5137719698be9725dfc457530aff608a5fc10a09a6a5faab8a1`.

Durable receipt: `CPU-G90-GPT2-BATCHED-THROUGHPUT-ARTIFACT-RECEIPT-20261031.json`. Runtime environment copy and discrepancy note are preserved beside it.

Frozen result: **engineering PASS, correctness PASS, BATCHING_NO_GO**. All 240 responses and 1,920 generated tokens matched. Batch2 achieved 1.023534× throughput versus batch1, below the 1.20× threshold. Batch4/8/12 were slower. No qualifying batch size exists.

Evidence caveat: archived `cpu_g90_environment.txt` says Transformers 4.48.4 while result JSON runtime metadata says 4.48.3; the discrepancy is explicitly documented and neither side is silently normalized.

This final qualification verifies exact archive receipt, frozen G70/source identities, G90 tests, isolation/FSA, F139 custody and Go Linux/Windows regressions. It does not rerun the benchmark or alter the measured classification. Scientific acceptance remains NOT_GRANTED and promotion remains false.
