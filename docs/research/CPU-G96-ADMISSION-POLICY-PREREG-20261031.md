# CPU G96 — frozen admission-policy experiment (development only)

## Custody
Parent G95 source: commit `8d1bf38854a519050838140b22a0304695305fcb`; G95 original-model run `41228835448`, artifact `13052847529`. G95 frozen verdict `MULTIPREFIX_LRU_NO_GO`; G93/G94 positive repeated-prefix results remain separate. G95 is **not** production-admissible. G95 final Linux PASS, Windows qualification still required. No controller, model, inference-server, threshold, protected-main, or promotion changes.

## Research question
Can admission decisions under a strict four-entry/86,114,304-byte resident-KV budget improve cold-miss tail latency and retain aggregate acceleration on genuinely new, interleaved four-prefix traffic?

## Hypotheses
H0: None of the policies passes all frozen performance, memory, and exactness constraints. H1: An admission policy passes *all* criteria on independently selected held-out streams. No policy may be selected based on the final held-out cohort.

## Controlled policies
1. No cache (reference).
2. Conventional exact-key LRU (capacity 4).
3. Admit-on-second-use (capacity 4; first request bypasses residency, deterministic count).
4. Frequency-aware admission (capacity 4; fixed window, tie-breaking by immutable prefix digest).
5. Cost-aware request admission (capacity 4; deterministic predicted reuse benefit versus measured prefix-prefill and copy cost, calibrated on development-only cohort).

All policies must use identical original GPT-2 FP32 weights, tokenizer, prompt tokens, generation settings, 2 intra-op/1 inter-op threads, 3-core affinity, CPU/runtime versions, full-response accounting and per-request deep-copied KV. No learned model, adaptive thresholds, workload peeking, per-arm prompt changes, or hidden warmup.

## Cohort and preregistration boundaries
Freeze independent GSM8K question ranks and exact stream SHA-256 **before implementation and measurement**. G96 ranks must not overlap G95 [264,275] or prior screened cohorts. Development/calibration and final held-out streams must be disjoint; held-out ordering and outcomes remain sealed until all policy logic and thresholds are committed. Include short-reuse, bursty, four-prefix interleaving and working-set-overflow stress strata. Match response count and generated tokens across arms; fixed seeded paired repetitions; report each stratum and overall, never replace worst-case with mean.

## Acceptance (unchanged G95 minimums)
- Exact generated-token parity on every original-model response, no aliasing or resident mutation; capacity and byte budget never exceeded.
- Median throughput ratio >= 1.15 versus uncached.
- Minimum paired-request speedup >= 0.90.
- p95 latency ratio <= 1.10.
- Total CPU ratio <= 1.10.
- Maximum sampled RSS ratio <= 1.15.
- Report hit/miss/eviction/admission, prefill, clone, decode and admission-decision overhead, wall/CPU times, RSS and resident bytes.
- Every stratum must pass correctness and safety; no post-hoc threshold waiver. Failure in any required criterion => NO_GO.

## Execution sequence
A. Verify G95 final Windows qualification and original artifact SHA, identify latest exact source identity and prior cohort disjointness.
B. Commit sealed cohort selection and independent development/held-out provenance, deterministic stream manifests and exact source hashes.
C. Implement all five policies and focused adversarial unit tests; source admission and static contract qualification.
D. Run pinned original-model paired measurements once on the held-out cohort, preserving raw JSON/environment artifacts and hashes.
E. Run mandatory Linux/Windows integration regression, produce capacity/policy adjudication and immutable repository receipt.
F. Keep draft and development-only until all gates pass. No automatic production integration or scientific acceptance.

The G95 4-entry aggregate improvement is *not* G96 evidence. Admission policy alone may not fix cold-miss overhead; this experiment can legitimately conclude NO_GO.
