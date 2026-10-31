# CPU GPT-2 G86 — native SDPA versus eager attention

Prospective preregistration frozen before executable source, tests, workflows or original-model measurements, 2026-10-31. CPU GPT-2 LLM Evaluation only; separate from RTX GPU ACC, FORGE controller/autonomy and native Wingless/Yggdrasil research.

## Hypothesis and novelty

Test whether Transformers 4.48.3's original GPT-2 scaled-dot-product attention (SDPA) backend reduces full-response CPU latency compared with the eager attention implementation while preserving exact original greedy outputs. This is a real execution-backend hypothesis, not another thread-only study, quantized approximation, synthetic kernel microbenchmark, model architecture change or learned intelligence claim.

Transformers 4.48.3 includes an SDPA attention interface for GPT-2. The comparison must use the framework's actual selected backend, with output_attentions disabled and no head mask so the SDPA route does not fall back to eager. Verify the selected config and instrument the SDPA call path during admission; a silent fallback is BLOCKED_IMPLEMENTATION, never an SDPA result.

## Immutable source, baseline and cohort

- Exact qualified CPU G70 baseline: 20a540d0241519e2e9d90ace868ffd6db60bd065. Preserve all G54-G70 sources unchanged.
- Original pretrained openai-community/gpt2 revision 607a30d783dfa663caf39e06633721c8d4cfcd7e; original safetensors SHA256 248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707. Reuse the seven-file G55 staging/manifest and verify original weights.
- Original MIT GSM8K test source commit 3101c7d5072418e28b9008a6636bde82a006892c; raw bytes 749738; SHA256 3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14.
- Use the exact G82 hash-ranking algorithm and seed G68-GPT2-HELDOUT-20261030:, selecting new original rows at ranks 156-167. Verify the exact original G68 and G70 first-use partition records and all prior disjoint rank ranges through G82 ranks 144-155. No reuse, synthetic prompts or substitute data.
- Each prompt is original G55 shared prefix concatenated with the first 64 original GPT-2 question token IDs; add_special_tokens=False. Full FP32 pretrained GPT-2; exactly eight new greedy output tokens. No weight changes, training, quantization, approximation, caching across prompts, alternate tokenizer, or hidden model calls.

## Runtime and matched experimental design

- Native x86_64 Linux ubuntu-24.04, Python 3.11, torch 2.5.1+cpu from the official CPU wheel index, Transformers 4.48.3, huggingface_hub 0.30.2, safetensors 0.5.3, tokenizers 0.21.1, psutil 7.1.3; verify exact versions, torch.version.cuda is None and pip check.
- Exactly three logical CPUs for all arms, process affinity set/read back; PyTorch inter-op threads fixed at one. No GPU. Record processor and OS/kernel identity.
- Load two separate original pretrained model instances from the same verified files, one configured attn_implementation=eager and one attn_implementation=sdpa. Verify every parameter is FP32, the model config records the intended backend, parameter/checkpoint manifests match, SDPA call counter is nonzero only for SDPA arms, eager call counter is nonzero only for eager arms, and no SDPA fallback occurs.
- Six diagnostic/comparison arms: eager1, eager2, eager3, sdpa1, sdpa2, sdpa3. Suffix is torch intra-op thread count. Primary comparison is preregistered as sdpa2 versus eager2; other arms characterize interaction only and cannot replace the primary contrast after results.
- Charge torch.set_num_threads inside every timed request. Timer includes prompt prefill, all seven cached original forwards, attention-mask construction, eight argmax selections and response assembly.
- Exactly 12 original questions x 4 counterbalanced/rotated repetitions x 6 arms = 288 original full-response measurements, 2304 original generated tokens and 48 six-arm paired records. Rotate/reverse arm order deterministically. Require all eight token IDs identical across every arm/repetition for each prompt; save full original paired timings, input/output hashes and environment. No outlier exclusion.

## Frozen acceptance

SDPA_PASS only if every condition holds:

1. Source/model/dataset identity, exact backend selection, actual SDPA kernel dispatch, native CPU runtime, fixed affinity, complete cohort and 48 paired records all PASS.
2. All 288 full original responses and all 2304 generated tokens have exact greedy-token parity across eager/SDPA and all thread counts.
3. Primary sdpa2 median full-response speedup versus eager2 is at least 1.15x.
4. Minimum paired eager2/sdpa2 speed ratio is at least 0.90x.
5. sdpa2/eager2 p95 latency ratio is at most 1.10x.
6. Sampled maximum RSS ratio is at most 1.10x.
7. Total process CPU time ratio is at most 1.25x.

Any threshold miss is SDPA_NO_GO. Token mismatch is FAIL_EXACTNESS. Wrong backend, fallback, runtime/source mismatch or incomplete cohort is BLOCKED_IMPLEMENTATION or BLOCKED_ENV. No threshold, cohort, prompt or arm changes after measurement; no alternate arm may be promoted as the primary result.

## Interpretation and authority

A pass demonstrates only a faster exact-output eager-to-SDPA backend change for this pinned GPT-2 CPU runtime, host, prompt cohort and resource budget. It does not establish Windows or ARM transfer, other model families, production serving throughput, energy efficiency, cognition, general intelligence, native Wingless/Yggdrasil capability, model integration or scientific acceptance.

Keep this research-only and DRAFT/UNMERGED regardless of result. Preserve prior G71-G85 results and qualified G70 sources. No protected-main change, controller/queue mutation, model promotion, deployment, paid API, broker, GPU study or Wingless/Yggdrasil source mutation is authorized. This preregistration's own immutable Git commit must precede all G86 executable, test and workflow source.