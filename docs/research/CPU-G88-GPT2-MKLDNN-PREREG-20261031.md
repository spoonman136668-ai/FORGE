# CPU GPT-2 G88 — oneDNN/MKLDNN backend enablement screen

**Prospective preregistration — 2026-10-31.** This document is committed before G88 executable source, tests, workflows or measurements. Research-only CPU LLM evaluation, isolated from RTX GPU ACC, FORGE autonomy/controller, and native Wingless/Yggdrasil research.

## Hypothesis and scope

Test whether PyTorch's native CPU oneDNN/MKLDNN dispatch, when enabled, improves original GPT-2 FP32 full-response latency versus the same PyTorch runtime with MKLDNN dispatch disabled, at an identical CPU thread and affinity budget.

This is a backend-dispatch comparison, not quantization, model conversion, training, Inductor compilation, attention-backend substitution, altered decoding, or synthetic operator microbenchmark.

The candidate is admitted only if profiling on authentic model requests proves that the enabled arm actually dispatches one or more MKLDNN operations and that the disabled arm dispatches none. If profiling cannot establish that contrast, classify `BLOCKED_IMPLEMENTATION`; do not treat a boolean configuration change alone as proof of backend execution.

## Immutable baseline and source cohort

- Qualified G70 CPU baseline: `20a540d0241519e2e9d90ace868ffd6db60bd065`; preserve G54–G70 source blobs unchanged.
- Original pretrained `openai-community/gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`; original safetensors SHA-256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`.
- Original MIT GSM8K test revision `3101c7d5072418e28b9008a6636bde82a006892c`; raw dataset SHA-256 `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`.
- Reuse the exact frozen G82/G86/G87 original rank algorithm and seed `G68-GPT2-HELDOUT-20261030:`. Select ranks **180–191 inclusive**, after G87 ranks 168–179; verify previous first-use partition contracts and disjointness. No prompt reuse, synthetic substitute or post-result cohort changes.
- Use original G55 shared prefix and first 64 original GPT-2 question token IDs (`add_special_tokens=False`), unchanged FP32 weights/tokenizer, original greedy decode of exactly eight new tokens. No model training, weights change, quantization, speculation, caching across prompts, alternate tokenizer or changed decoding policy.

## Runtime and matched comparison

- Native `ubuntu-24.04` x86_64 CPU only; Python 3.11, PyTorch `2.5.1+cpu`, Transformers `4.48.3`, huggingface-hub `0.30.2`, safetensors `0.5.3`, tokenizers `0.21.1`, psutil `7.1.3`. Verify exact versions, `torch.version.cuda is None`, dependency health and oneDNN build/runtime availability.
- Same three logical CPUs and affinity for both arms; PyTorch intra-op threads = 2, inter-op threads = 1. Verify/read back all settings. Thread setting cost is charged inside every request.
- Load separate source-verified, parameter-identical original FP32 model instances for each arm. The only independent variable is `torch.backends.mkldnn.enabled`: `enabled` versus `disabled`.
- Profile warmup and a fixed sample of requests using PyTorch CPU profiler; store operator event keys/counts and assert that enabled execution contains actual MKLDNN-dispatched operator events, while disabled execution contains none. No synthetic calls or extra measured work are included in latency.
- Two arms: `mkldnn_enabled2` and `mkldnn_disabled2`. Exactly 12 original prompts × 4 counterbalanced repetitions × 2 arms = **96 original full responses, 768 generated tokens and 48 paired records**. Same request path, prompt tensors, model state, cache semantics, thread budget and full eight-token decode.
- Verify all eight generated token IDs are identical for every pair and repetition; fail closed on any mismatch. Record full paired timings, input/output hashes, selected source rows, per-arm profiler counts and event names, CPU and wall time, sampled RSS, exact runtime/model/data manifests.
- Warm both modes identically before paired trials; rotate arm order deterministically. Do not exclude outliers. Report medians, p95, worst paired ratio, cumulative process CPU and sampled RSS.

## Frozen acceptance

`MKLDNN_PASS` only when **all** criteria hold:

1. Exact source, G70, preregistration, model-weight, dataset and disjoint-rank identity; native pinned CPU runtime, fixed three-core affinity and complete 48 paired records.
2. Actual oneDNN/MKLDNN operation dispatch is proven in the enabled arm and absent from the disabled arm on authentic model operations.
3. Exact greedy token parity for all 96 full original responses and 768 generated tokens.
4. Median full-response speedup enabled versus disabled >= **1.15×**.
5. Minimum individual paired speed ratio disabled/enabled >= **0.90×**.
6. p95 enabled/disabled latency ratio <= **1.10×**.
7. Sampled maximum RSS ratio <= **1.10×**.
8. Total process CPU time ratio <= **1.25×**.

Any speed, p95, resource or exactness threshold miss is `MKLDNN_NO_GO` (token mismatch also explicitly `FAIL_EXACTNESS`). Missing actual backend dispatch, unsupported runtime, profiler ambiguity, source/model/dataset drift or incomplete cohort is `BLOCKED_IMPLEMENTATION` or `BLOCKED_ENV`. No arm, cohort, threshold, backend flag or workload substitution is permitted after measurement.

## Interpretation and authority

A pass establishes only the effect of enabling the actual oneDNN/MKLDNN path for this pinned original GPT-2 FP32 CPU workload, runtime and host. It does not establish another CPU architecture, Windows/ARM transfer, another model family, production-serving gains, energy efficiency, training-held-out generalization, cognition or intelligence.

Keep research-only and DRAFT/UNMERGED regardless of result. Preserve all G71–G87 records and qualified G70 files unchanged. No protected-main change, model promotion, deployment, controller/queue mutation, paid API, broker, GPU experiment or Wingless/Yggdrasil source mutation is authorized.
