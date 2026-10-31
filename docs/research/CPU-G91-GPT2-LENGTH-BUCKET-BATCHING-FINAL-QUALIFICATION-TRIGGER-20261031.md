# G91 original measurement receipt and final qualification — 2026-10-31

Original-model workflow #41218237089 completed successfully. Artifact #13049236298 was recovered and inspected. ZIP SHA-256: `964d5ea6fe8e84dc4403e547f6c78af0f52cd2a57b283913e54135efddeecba2`; original result JSON SHA-256: `3a55a6f5702165fc9473ec20b6bb8a1f2afdd4491d3cbf1187529f93fa727f0e`; archived environment SHA-256: `19b33dd9d742e2b0540403bc0d84c12c04ae1850acb2d7ea8ccba7b6bc572774`.

Durable result receipt: `CPU-G91-GPT2-LENGTH-BUCKET-BATCHING-ARTIFACT-RECEIPT-20261031.json`; runtime manifest: `CPU-G91-GPT2-LENGTH-BUCKET-BATCHING-ENVIRONMENT-20261031.txt`.

Frozen disposition: **engineering PASS, correctness PASS, LENGTH_BUCKET_NO_GO**. Length bucketing reduced padding tokens and beat same-size random grouping, but absolute full-cohort throughput was only 1.007404× batch1 for batch2 and 0.946625× for batch4; neither met the 1.20× frozen requirement. All 240 responses/1,920 tokens matched exactly. No thresholds or experiment cohorts changed.

This final workflow performs immutable receipt/source checks, G91 unit tests, isolation/FSA, F139 custody and full Go tests/race/vet/build on Linux and Windows. It does not rerun inference. Scientific acceptance remains NOT_GRANTED and promotion remains false.

Receipt-only Linux/Windows final qualification workflow is now committed. Start a new final verification run from this exact branch head.

Regression test fixture whitespace assertions were corrected; restart final receipt-only Linux/Windows qualification against this exact test blob.

Pinned G91 implementation source SHA was corrected to the authenticated Git blob; rerun final qualification.

Corrected the compact-source receipt assertion fixture and pinned its exact test blob; rerun final qualification.
