# ACC-44 — original U10 holographic associative memory: frozen protocol

**Prospective first commit; no implementation or measurements yet.**

## Source and independence

Research parent: ACC-34 draft PR #1131 at commit `45b5d8173538a566bf0f63a8e2ade2dedb6e6166`. Original AC-08 portfolio `research/ac07_sourcefree/ac08_portfolio.py`, blob `5126c860771fb024ccfc14c3f7ee8925edf29787`. The original enumeration (one-based) names **U10 "holographic associative memory"** and **U13 "fixed-size KV sketches"**. Verify both names by Python AST before any benchmark. U13 was measured separately in ACC-43 with negative general resource findings. ACC-42 attribution error remains preserved; do not reuse those results here.

Hypothesis: can a 512-byte circular-convolution holographic associative memory retain and recall independently observed key-to-class pairs more efficiently than full-key exact indexing and a same-size nonconvolution superposition control, at matched retrieval quality?

## Frozen data and native arms

All methods receive the same public, deterministic random 31-bit keys with independent uniformly random class labels 0..15 and no repeated keys in one episode. Trial seeds **92201, 92203, 92207, 92209, 92211**. Session generator namespace `0x19ae6776413bfa52` and class namespace `0xc12d0885ee13d5a7`. Key vector namespace `0x4455acce1020fe76`, value codebook namespace `0xa6c1f4e2798b035d`. No key/label association is derivable from the key alone. Compare three cohorts: LIGHT 24 inserted associations; FULL 64; OVERLOAD 128. Each fresh episode ends with **256 queries**, evenly split into present keys and guaranteed absent keys (disjoint high-bit domain). **32 reset episodes per cold process**.

Exactly four arms, each with 512 logical bytes of persistent candidate state:
- **EXACT_ONE**: 64 eight-byte slots (uint32 key, uint8 class, uint8 occupied, uint16 insertion age), conventional one-bucket, 4-way exact-key table.
- **EXACT_TWO**: same 64 full-key slots with two independently hashed candidate 4-way buckets, deterministic least-age eviction.
- **XOR_SUPERPOSE**: 64 int64 counters, incremented by procedurally generated bipolar keySign[i] × classSign[i]; classify by maximum 16-class dot product after key unbinding; reject unless maximal dot >= 0.65×64.
- **HRR_CCONV**: **holographic reduced representation** using 64 int64 counters. Bind class and key vectors by **integer circular convolution** `bound[j]=sum_i key[i]*value[(j-i) mod 64]`, superpose bound vectors, retrieve by **circular correlation** `retrieved[j]=sum_i memory[(i+j) mod 64]*key[i]`, then score all 16 class vectors by dot product; reject unless best score >= 0.65×64×64. No original keys, oracle lookup or helper index retained by either superposition candidate.

Independent exact auditing oracle receives public inserts and supplies only scoring labels **after** every candidate prediction. Its source-generation, map build, and lookup overhead are charged to every worker. Record source SHA-256, oracle truth SHA-256, output trace SHA-256, exact-present recall, wrong-value count, false-positive missing-key count/fraction, logical state bytes, peak OS physical RSS and process CPU.

## Qualification and locked decision

Run **60 cold workers per OS** (5 paired seeds × 3 cohorts × 4 arms), each 32 full episodes, on GitHub-hosted Linux and Windows with native Go 1.25.5; rotate AB/BA arm order. Whole-child CPU from parent process user+system time, parent wall spawn-to-exit, Linux VmHWM and Windows PeakWorkingSetSize, not allocator estimates. Verify equal input/oracle digest for all arms and exact cross-platform input/output parity for all 60 workers. Missing CPU/RSS, identity, trace, workers, nonfinite metrics or source custody => `ACC44_U10_BLOCKED`.

Restricted **U10 native Go engineering positive** only if **every cohort on both OS** satisfies: HRR wrong-value deliveries zero; absent-key false positive fraction <=0.005; median exact-present recall >= max(EXACT_ONE, EXACT_TWO, XOR_SUPERPOSE) median recall minus 0.01; LIGHT HRR recall >=0.95; median full-worker CPU <=0.90× the fastest median CPU among all three controls; median physical RSS <=1.10× the same fastest control; exactly 512 persistent logical state bytes. Five seeds medians, no hand-picked subset.

Valid measurements failing any criterion => `U10_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN`. Qualified numeric positive => `U10_RESTRICTED_NATIVE_GO_ENGINEERING_POSITIVE_ONLY`, **never** native Wingless/Yggdrasil model acceleration, semantic task performance, training efficacy, scientific first-use or production admission. This is synthetic, source-free bounded storage research.

Freeze this document **before executable**. Later commits add isolated Go code, source-hashed original-name assertion, Go tests/vet/build, retained 36-candidate source-negative regression, exact native resource measurements, independent cross-platform reconciliation and raw receipts. Do not change this protocol after observing results. No protected main, original models, controller, F139 owner, FORGE autonomy, accepted scientific registry or paid APIs touched. Keep draft/unmerged.
