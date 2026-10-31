# CPU GPT-2 G94 — shared-prefix KV reuse versus cohort-size scaling

**Prospective preregistration — 2026-10-31.** Frozen before G94 implementation, tests, workflow and measurement. This is an extension/robustness study of G93's positive shared-prefix result, not a new claim that G93 already generalizes.

## Hypothesis

G93 established a 2.329× median cohort speedup for a single cohort of twelve requests sharing the exact G55 instruction prefix. G94 measures how much of that benefit survives when the same twelve-request workload is served in smaller independent cohorts.

For cohort sizes 2, 4, 6 and 12, candidate requests share the same exact prefix only within their cohort. A fresh prefix KV state is computed per cohort; per-request cache copies, prefix prefill and the request suffix/decode are charged. The baseline recomputes the complete prefix+suffix prompt independently per request. This isolates the amortization effect of group size and determines its break-even curve.

## Immutable identities and disjoint cohort

- Qualified original CPU baseline G70: `20a540d0241519e2e9d90ace868ffd6db60bd065`; preserve G54–G70 source files byte-identically.
- Original pretrained `openai-community/gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`; weights SHA-256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`; FP32.
- Original MIT GSM8K test revision `3101c7d5072418e28b9008a6636bde82a006892c`; raw SHA-256 `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`.
- Exact G68–G93 SHA ranking and seed `G68-GPT2-HELDOUT-20261030:`; next disjoint ranks **252–263 inclusive**. Verify G68/G70 partition contract and no overlap with any preceding G82–G93 cohort. Exactly twelve new source questions.
- Preserve G55 exact shared prefix, tokenize prefix and questions independently without special tokens, original FP32 weights/tokenizer, original cached greedy decoding and exactly eight new tokens. No changes to model or decoder.

## Arms and schedule

- Native Ubuntu 24.04 x86_64; Python 3.11; PyTorch `2.5.1+cpu`; Transformers `4.48.3`; huggingface-hub `0.30.2`; safetensors `0.5.3`; tokenizers `0.21.1`; psutil `7.1.3`; CUDA unavailable.
- Fixed identical three-logical-CPU affinity; PyTorch intra-op 2, inter-op 1. Read back settings.
- Baseline arm `full_prompt_all12`: twelve independent full prompt prefill + eight-token decode requests in a fixed sequential pass.
- Candidate arms `shared_prefix_cohort2`, `shared_prefix_cohort4`, `shared_prefix_cohort6`, `shared_prefix_cohort12`. For each arm, partition the same twelve original questions into deterministic contiguous groups of size N (group membership fixed across repetitions). For every group: compute the exact common prefix cache once; deep-copy its full KV state for each request; run each question suffix with exact absolute positions and mask; complete independent eight-token greedy decode. A fresh prefix cache is built for each group in every repetition.
- Candidate full-workload time includes all prefix prefill calls, cache clones, suffix prefill, cached decoding and group scheduling. Thus N=2 pays six prefix builds; N=4 pays three; N=6 pays two; N=12 pays one. Model/tokenizer load and tokenization are performed outside arms equally and reported separately.
- Before timing, compare next-token logits for full prompt versus prefix-cache + suffix for all twelve prompts; first argmax tokens must match. Warm all arms equally. Every final token sequence must be bit-identical to the corresponding full-prompt baseline output in every repetition.
- Four complete paired repetitions per arm; fixed rotated arm order; **12 questions × 4 repetitions × 5 arms = 240 full original responses and 1,920 generated tokens**. Keep per-group and per-request timing, every cache setup/copy cost, CPU time, sampled RSS, prefix/suffix IDs/hashes and model/data/runtime identities.
- Report total-workload cohort throughput, requests/sec, per-request latency, p95 amortized request latency, total CPU, sampled RSS and total prefix setup cost for every N. No inference profiler inside timed arms, no outlier removal.

## Frozen acceptance

A cohort size qualifies only if all conditions hold:

1. Exact model/data/runtime/G70 identities and disjoint ranks 252–263, fixed CPU budget and complete four repetitions.
2. Exact full-prompt and prefix/suffix token decomposition; exact positions, masks and independent cache-copy isolation.
3. All 240 outputs/1,920 generated tokens match exactly and every first greedy token matches.
4. Full twelve-request workload throughput vs `full_prompt_all12` >= **1.15×** after every per-group prefix and cache-copy cost.
5. Minimum individual request speedup after allocating its cohort prefix-build cost equally across group members >= **0.90×**.
6. p95 amortized request latency ratio <= **1.10×**.
7. Total process CPU ratio <= **1.10×**; maximum sampled RSS ratio <= **1.10×**.

`KV_COHORT_SCALE_PASS` if one or more sizes qualify. Report every size and choose the fastest qualifying cohort (ties smaller size). Otherwise `KV_COHORT_SCALE_NO_GO`. Exactness/cache isolation failure is `FAIL_EXACTNESS_OR_ISOLATION`; environment, source or incomplete-run errors are blocked, never treated as NO-GO. No threshold, size or workload edits after measurement begins.

## Interpretation and authority

This tests the break-even/scaling curve for repeated identical-prefix cohorts, not unrelated user traffic, cold single-request inference, other model families or production serving. G93's twelve-request result remains separately valid; G94 cannot retroactively alter it. Neither result implies scientific acceptance, intelligence or native Wingless/Yggdrasil progress.

Research-only, DRAFT/UNMERGED. No protected-main, deployment, controller/queue, paid API, broker, model training, promotion or scope-expansion authority is granted.
