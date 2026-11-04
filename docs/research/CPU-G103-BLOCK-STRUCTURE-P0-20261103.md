# CPU G103 P0 — Exact immutable KV block structure discovery

**State:** preregistered model-free implementation only. Novelty, savings,
inference correctness, latency benefit, and scientific acceptance are UNVERIFIED.

Retired G101 full-prefill extraction and rejected G102 XOR/zlib
base-state reconstruction MUST NOT be reopened. G103 instead asks whether
**exact byte-identical substructures** can be found across independently
computed KV states and reused via content identity.

Distinct arms are (1) uncompressed independent states, (2) independent
zlib-6 state compression, (3) conventional fixed 256-byte hash-addressed
blocks, and (4) content-defined variable blocks (minimum 64, average
256, maximum 512). All blocks, pool identity metadata, references and
per-state identity hashes count toward modeled storage. Copy-on-write
append and actual inference latency are NOT part of P0. Hash collisions
fail closed by verifying byte equality before sharing. Reassembly
checks every block and complete original-state hash.

The adaptive partitioning is a **hypothesis**, not an established novelty
or performance gain. Fixed-block content-addressing is an explicit
conventional comparator. The model-free P0 test must exercise repeated,
nonshared, mutated/corrupted, forced-hash-collision, and no-win inputs.

Next original-model gate must first freeze real FP32 GPT-2 prefix
selection and KV layout; compare fixed vs adaptive on *independent
correct* KV tensors. Require exact reconstruction and count full
physical bytes, reference/identity metadata, per-state hashes, transient
allocations, CPU costs, and original-model decode impacts. Do not claim
savings using only deduplicated payload bytes. Include identical-prefix
positive control and unrelated-prefix negative control; do not let
duplicate requests masquerade as cross-prefix generalization.
Preregister GO/NO_GO before original-model use and retain mandatory
Linux/Windows regression. Development only; protected ranks and
promotion remain blocked.

G103 is a distinct falsifiable structural-reuse experiment, not
a continuation of G102's XOR formulation.
