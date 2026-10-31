# CPU GPT-2 G93 — shared-prefix KV cache reuse across independent requests

**Prospective preregistration — 2026-10-31.** Committed before G93 executable source, tests, workflow or original-model measurement. CPU LLM inference-systems research only; separate from RTX GPU ACC, FORGE autonomy/controller work and native Wingless/Yggdrasil research.

## Rationale and hypothesis

G80's original-model diagnostic found GPT-2 prompt prefill dominant (81.10% median phase share). G90/G91 showed independent-request batching and length-aware grouping did not qualify. G92's native GELU replacement produced only 1.0355× median prefill improvement and 1.0217× full-response improvement, below frozen thresholds.

The established G55 GPT-2 harness defines a common fixed instruction prefix reused across distinct suffix questions. G93 tests whether the model can precompute this identical causal prefix once, retain its per-layer key/value state, and reuse independent copies of that cache for the suffix of each request. The optimization target is repeated computation of the same prefix tokens, not the underlying per-token decoder.

This is not batching, KV quantization/compression, changing weights, attention implementation, precision, sampling, tokenizer, or generation length. Each request remains an independent sequence and gets its own cloned prefix cache before suffix processing.

## Immutable identity and new cohort

- Qualified original CPU baseline: G70 commit `20a540d0241519e2e9d90ace868ffd6db60bd065`; G54–G70 source trees byte-identical.
- Original `openai-community/gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`; safetensors SHA-256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`; FP32.
- Original MIT GSM8K test revision `3101c7d5072418e28b9008a6636bde82a006892c`; raw SHA-256 `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`; 749,738 bytes.
- Exact G68–G92 SHA-ranking protocol, seed `G68-GPT2-HELDOUT-20261030:`; select new disjoint ranks **240–251 inclusive**. Verify G68/G70 partition contracts and disjointness from all prior measured rank intervals. Exactly twelve distinct original questions, with no replacement or post-result reselection.
- Reuse the immutable G55 shared instruction prefix exactly; append each selected original question as its independent suffix. Tokenize prefix and suffix independently with the same tokenizer and `add_special_tokens=False`; record prefix/suffix IDs and hashes. Full-prompt baseline input is the exact concatenation of the same token IDs.
- Original pretrained FP32 weights, tokenizer, CPU attention implementation, KV-cache dtype, greedy argmax and exactly eight newly generated tokens remain unchanged.

## Arms and execution protocol

- Native Ubuntu 24.04 x86_64; Python 3.11; PyTorch `2.5.1+cpu`; Transformers `4.48.3`; huggingface-hub `0.30.2`; safetensors `0.5.3`; tokenizers `0.21.1`; psutil `7.1.3`. Verify exact runtime, `torch.version.cuda is None`, and `pip check`; preserve environment and host manifests.
- Identical fixed process affinity of three logical CPU cores; PyTorch intra-op threads=2 and inter-op threads=1; verify/read back every arm. CPU only.
- Arm A `full_prompt_prefill2`: for each of the twelve independent requests, call original GPT-2 on prefix concatenated with that question suffix, then perform seven cached forward steps plus greedy token selection to produce exactly eight new tokens. The entire twelve-request cohort is timed.
- Arm B `shared_prefix_kv_reuse2`: once per twelve-request cohort, run the unchanged model on the common prefix and create one immutable prefix KV cache. For each request independently, deep-copy that cache (copy time is charged), supply that question's suffix tokens, an all-valid attention mask with exact total past+suffix length, and explicit absolute position IDs beginning at the prefix length. Continue the same eight-token greedy decode with request-specific cache, mask and absolute positions. Do not share mutable request cache state.
- Candidate cohort wall and process CPU times include prefix prefill exactly once, all cache-copy overhead, suffix forward, all cached decode and per-request scheduling. Baseline cohort time includes all twelve independent full-prompt prefill and decode paths. Tokenization/model loading are identical and outside both arms' timed intervals; record separately.
- Before timing, verify next-token logits on each original full prompt versus prefix-cache-plus-suffix execution (max absolute logit difference recorded; exact next-token identity required); warm both arms equally and verify all eight generated token IDs for all twelve questions.
- Exactly twelve original requests × four paired cohort repetitions × two arms = **96 full original responses, 768 generated tokens and 48 paired request records per arm**. Rotate arm order by repetition. Rebuild the prefix cache once for each candidate cohort trial so its setup cost is charged every time.
- Record prefix token count; suffix token counts; each request's source rank, input/output hashes, cache-copy time, suffix-prefill time, cached-decode time, individual wall/CPU time; each cohort's full wall/CPU, prefix setup time, sampled maximum RSS and environment. No outlier removal.
- Report median cohort throughput speedup, per-request latency speedups, p95 request latency including an equal 1/12 allocation of shared prefix setup, raw per-request execution p95, process CPU per generated token, and sampled RSS. Clearly distinguish twelve-request shared-prefix cohort economics from single-request performance.

## Frozen acceptance

`SHARED_PREFIX_KV_PASS` requires every condition:

1. Exact pinned model/data/runtime/source identity, ranks 240–251 disjoint from prior cohorts, complete 4 paired cohort trials and verified CPU limits.
2. Prefix and suffix token IDs exactly reproduce the full concatenated prompts; identical per-request absolute position IDs and causal attention semantics are verified.
3. Prefix KV cache is independently deep-copied per request; no mutable cache crosses request boundaries.
4. For every question, original full-prompt logits choose the same first greedy token as prefix-cache reuse; all **96** full responses and **768** generated tokens have exact token-ID parity.
5. Median twelve-request cohort throughput speedup >= **1.15×** versus full-prompt baseline, with candidate prefix setup and cache-copy cost included.
6. Minimum paired per-request full-response speedup, after allocating 1/12 of shared prefix setup, >= **0.90×**.
7. Candidate p95 amortized per-request latency / baseline p95 <= **1.10×**.
8. Candidate total process CPU time / baseline <= **1.10×**.
9. Candidate maximum sampled RSS / baseline <= **1.10×**.

Any threshold miss is `SHARED_PREFIX_KV_NO_GO`. Any token/position/mask/cache-isolation mismatch is `FAIL_EXACTNESS_OR_ISOLATION`. Missing original identities, incomplete cohort or unavailable CPU controls is `BLOCKED_ENV` / `BLOCKED_IMPLEMENTATION`. No post-result threshold, prompt, cohort or cache semantics may change.

## Interpretation and authority

A pass establishes only a repeated-identical-prefix inference optimization for this pinned GPT-2 FP32 CPU workload and twelve-request cohort. It does not establish lower cold single-request latency, generic traffic benefits when prefixes differ, other-model/architecture transfer, production serving, energy efficiency, intelligence or native Wingless/Yggdrasil capability.

Keep research-only and DRAFT/UNMERGED. Preserve G71–G92 evidence and all NO-GO/blocked results unchanged. No protected-main change, deployment, controller/queue mutation, paid API, broker, model training or promotion is authorized.
