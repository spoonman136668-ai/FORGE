# CPU G103 P1 — Frozen authentic GPT-2 structural-reuse diagnostic

**Preregistered BEFORE any original-model execution.** Distinct research
family after G101 and G102 NO_GO; protected data untouched. G103 P0
exact-head mandatory Linux/Windows regression PASSED at
`6ab8cb4c84b834bbbb9eb108ce495dc8afa93aed`, run 41750334528.

## One-shot original-model sampling

Pinned GPT-2 (G95 model revision, exact weights, torch 2.5.1+cpu,
transformers 4.48.3, 2/1 threads, 3-core affinity) computes actual FP32
KV tensors for three separate cold-pool groups:
(1) identical original G95 prefix twice, positive duplicate control;
(2) original G95 prefix plus first two fixed one-token variants from
G102's existing frozen `variant_tokens`, distinct-related development;
(3) three distinct original G95 prefix templates, unrelated control.
No new datasets or questions are retrieved. For each group reconstruct
every full original KV byte stream with exact SHA verification; disallow
shape-mismatched comparisons and changed original-model weights.

## Frozen comparison and decision

Compare conventional 256-byte fixed-block SHA256 sharing, adaptive
content-defined block boundaries (64/256/512), independently
zlib-6-compressed *whole* KV states, and raw independent KV. Every
mode is charged all block payload bytes, unique-block metadata,
all manifest references and state hashes. Exactly reconstructed
states are required. Timed construction, verification and restore
CPU/wall metrics are recorded, but single-pass timing is **diagnostic
only**, never a throughput or latency assertion. Full transient
allocator and Python overhead are not measured by modeled storage;
sampled process RSS is reported with this caveat.

Positive duplicate-only savings cannot trigger feasibility. A
`STRUCTURAL_FEASIBLE_DIAGNOSTIC` requires adaptive related-prefix
sharing to consume at most 90% of the smallest of raw states,
independent zlib and conventional fixed-block sharing; all group
integrity and control checks must pass. Otherwise return
`STRUCTURAL_NO_GO_DIAGNOSTIC`. Failures of the test harness, missing
data, unexpected identity, or corruption are engineering FAIL,
not scientific NO_GO.

Regardless of outcome, no protected heldout evaluation, inference
integration, production changes, autonomous deployment or scientific
acceptance is allowed. If the related-prefix arm fails, retire this
specific fixed/adaptive representation instead of repeatedly tuning it
without new independent evidence.
