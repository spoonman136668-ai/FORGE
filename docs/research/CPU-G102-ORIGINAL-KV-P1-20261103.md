# G102 P1 — Original GPT-2 exact-KV reconstruction feasibility

**Stage:** frozen engineering experiment design. **Not** original-model
results, protected first-use, or production acceptance.

P0 source has qualified on exact-head Linux/Windows. P1 uses the pinned
original unquantized GPT-2 FP32 checkpoint and G95 prompt family but no
protected or development question dataset. Four equal-token-length prefix
variants are derived by exactly one token substitution each at fixed
positions `(0,1,5,11)` with additions `(1,7,101,991)`. This intentionally
tests a maximally favorable *related-prefix* family. It is not a claim
about naturally diverse production traffic.

Serialize every original-model KV tensor as exact FP32 bytes, all 12
layers and K/V per layer. For each variant, require byte-exact recovery
of its independently computed state from a separately stored base plus
compressed XOR residual. SHA-256 verifies the full base and each target.

Strong storage controls: raw independent targets, independently
zlib-compressed target bytes (level 6), proposed full base bytes plus
zlib-compressed XOR residuals. The base is not free. Require proposed
base-inclusive bytes at least 10% below *both* controls for exploratory
`STORAGE_FEASIBLE_DIAGNOSTIC`; otherwise `STORAGE_NO_GO_DIAGNOSTIC`.
Compare encode/decode CPU and wall, raw-copy and standalone-zlib controls.
These single-pass measurements are exploratory only and do **not**
establish a throughput or latency improvement. Prefill, CPU RSS and
identity provenance are recorded separately; sampled RSS is not a
reliable full transient peak measurement.

This only tests whether the exact residual method has storage
potential on genuine GPT-2 tensors under favorable controlled
conditions. After exact-head Linux/Windows qualification, use existing
authorized original-model runners, record immutable source and
artifact receipt, validate complete results, and keep production and
protected data untouched. Do not automatically advance to more costly
experiments if storage fails against conventional compression.
