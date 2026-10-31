# G86 archive receipt recovery and final qualification trigger — 2026-10-31

The original G86 benchmark completed on the original source SHA `e01926b9c7e0169e097d60079c7bb21ee4bbda07`. The original GPU-free CPU measurement and focused tests succeeded. Its final workflow step failed only when pushing the receipt because the checkout deliberately had `persist-credentials: false`; the shell was not configured to use the provided `GH_TOKEN`.

No benchmark rerun was performed. The already-uploaded original artifact was recovered from run #41209091131 and independently ZIP-SHA256 verified:

- Artifact ID: `13045218225`
- ZIP SHA-256: `7002039320dd08e67b557baae6c2c744cdf5e130463e8efc68c7bdce250bba52`
- Original result JSON SHA-256: `98ee6eb1d394565043e0eafe035761a1583914e58cc104573d9e51916d4147a9`
- Machine-readable repository receipt: `CPU-G86-GPT2-SDPA-ARTIFACT-RECEIPT-20261031.json`
- Exact runtime manifest: `CPU-G86-GPT2-SDPA-ENVIRONMENT-20261031.txt`

The repository receipt Git blob is frozen at `742a70b313d24b0454687c7206aa0fe2982e49fb`. The final Linux/Windows regression validates that exact blob, the original G70/prereg/source identities, experiment classification and counts, plus full F139, isolation, Go test/race/vet/build requirements.

Frozen outcome remains **engineering PASS, correctness PASS, SDPA_NO_GO**. Primary SDPA2/eager2 median speedup is 1.008987619×, below the preregistered 1.15× requirement. No threshold, source, cohort, weights, model, or scientific acceptance has changed. This workflow is receipt verification only; it does not rerun inference.
