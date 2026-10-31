# CPU GPT-2 G92 — fused native tanh-GELU replacement for original GPT-2 NewGELU

**Prospective preregistration — 2026-10-31.** This contract is committed before the G92 executable, tests, workflow or original-model measurement. CPU LLM inference research only; distinct from the RTX GPU ACC and FORGE autonomy/controller programs and from native Wingless/Yggdrasil research.

## Motivation and hypothesis

G80's authenticated unprofiled phase measurements found median prefill share of 81.10% for the pinned original GPT-2 eight-token request. Its separate profiler named `aten::addmm`, `aten::mm`, CPU scaled-dot-product attention and `aten::tanh` among the leading operators. G81 tested phase-adaptive thread counts and was a NO-GO; G86 tested attention SDPA and found no qualifying gain; G87 tested fullgraph Inductor; G88/G89 tested oneDNN paths; G90/G91 tested batching and length grouping. None qualified.

Hugging Face GPT-2's pinned `NewGELUActivation` implements OpenAI GPT's tanh approximation as a Python-level chain:
`0.5*x*(1+tanh(sqrt(2/pi)*(x+0.044715*pow(x,3))))`.
PyTorch exposes a native CPU GELU primitive with `torch.nn.functional.gelu(x, approximate="tanh")`. G92 tests whether that native fused primitive can replace the exact NewGELU formula in the original GPT-2 MLP layers with identical greedy outputs and lower prefill/full-request CPU cost.

This is a narrowly targeted operator substitution. It is not a new model, weight approximation, training method, quantization method or claim of changed intelligence. Since the native GELU implementation may differ by a few floating-point ULPs, exact output-token parity is mandatory and any token mismatch fails closed.

## Immutable identities and disjoint data cohort

- Qualified original CPU source baseline: G70 commit `20a540d0241519e2e9d90ace868ffd6db60bd065`; do not modify G54–G70 source trees.
- Original pretrained model: `openai-community/gpt2`, revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`; safetensors SHA-256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`; FP32.
- Original MIT GSM8K test revision `3101c7d5072418e28b9008a6636bde82a006892c`; raw SHA-256 `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`; expected 749,738 bytes.
- Reuse exact G68–G91 deterministic SHA ranking and seed `G68-GPT2-HELDOUT-20261030:`; use next disjoint rank interval **228–239 inclusive**. Verify G68/G70 partition functions and no overlap with previously consumed ranks. Twelve original questions, no replacements or post-result reselection.
- Use original G55 shared prompt prefix, first 64 question tokens (`add_special_tokens=False`), original greedy argmax, KV-cache semantics and exactly eight generated tokens. Model weights, tokenizer, attention backend and all other model computations remain unchanged.

## Arms and execution protocol

- Native Ubuntu 24.04 x86_64; Python 3.11; PyTorch `2.5.1+cpu`; Transformers `4.48.3`; huggingface-hub `0.30.2`; safetensors `0.5.3`; tokenizers `0.21.1`; psutil `7.1.3`. Verify exact installed versions, `torch.version.cuda is None`, and `pip check`; preserve full environment and host details.
- Same three logical CPU affinity, intra-op threads=2 and inter-op threads=1 in both arms; verify/read back each. No GPU.
- Arm A `original_newgelu2`: unchanged GPT-2 `NewGELUActivation` module in each of the twelve MLP layers.
- Arm B `native_gelu_tanh2`: replace only each layer's `mlp.act` module with a stateless module whose forward is exactly `torch.nn.functional.gelu(x, approximate="tanh")`. Verify there are exactly 12 replacements and every other module, parameter, buffer, model config, tokenizer, attention path and state-dict tensor is unchanged. No model weight mutation.
- Before full measurement, execute both activations on a deterministic FP32 tensor sampled from the actual original GPT-2 MLP pre-activation values; record max/median absolute and relative activation error and output hashes. This diagnostic does not alter the acceptance criteria.
- Two arms receive identical input IDs, per-row independent sequence, same loaded original FP32 weights, same cache behavior and identical eight-token greedy decode. Warm both arms equally outside timed trials. Rotate paired arm order deterministically.
- Exactly 12 original prompts × 4 paired repetitions × 2 arms = **96 full original responses and 768 generated tokens**, 48 paired records. Record per-prompt input IDs hash, output token IDs hash, prefill wall/CPU, cached decode wall/CPU, full response wall/CPU, sampled RSS and per-layer activation identity.
- Prefill is the first model forward on the complete prompt. Cached decode is the following seven token-selection-plus-cached-forward steps. Token selection is timed separately; phase totals and full end-to-end request time are retained.
- Run profiler only on separate, unmeasured original request(s), counting `aten::gelu`, `aten::tanh`, `aten::pow`, and all operator self CPU times. Never profile timed trials. The fused arm must exhibit real native `aten::gelu` dispatch and a reduced `aten::tanh`/`aten::pow` chain; if operator events do not show the intended dispatch change, classify `BLOCKED_IMPLEMENTATION`, not a performance outcome.
- No outlier deletion, no warmup/timing mixing, no prompt or token-count changes.

## Frozen acceptance

`NATIVE_GELU_PASS` requires all conditions:

1. Exact G70/G92 source, preregistration, model weights and dataset identity; new disjoint ranks 228–239; complete 48 paired trials; pinned native CPU runtime and settings.
2. Exactly twelve MLP activation replacements, no change to any pretrained model parameter, buffer, config, tokenizer, attention backend or other computation.
3. Real native `aten::gelu` events in candidate authentic-model profiling; native `aten::tanh` and `aten::pow` activation-chain counts reduced relative to original path.
4. Exact greedy output token parity across all 96 full responses and all 768 generated tokens. Any token mismatch is `FAIL_EXACTNESS`.
5. Median prefill speedup candidate versus original >= **1.15×**.
6. Median full eight-token response speedup >= **1.10×**.
7. Minimum individual paired full-request speedup >= **0.90×**.
8. Candidate p95 full-request latency / original p95 <= **1.10×**.
9. Candidate sampled maximum RSS / original <= **1.10×**.
10. Candidate total process CPU time / original <= **1.10×**.

Any threshold miss is `NATIVE_GELU_NO_GO`; no change to thresholds, source, prompts or implementation after initial measurement. Missing real native dispatch, source/runtime drift or incomplete cohort is `BLOCKED_IMPLEMENTATION` / `BLOCKED_ENV`. No post-hoc relaxed numeric tolerance can override token exactness.

## Interpretation and authority

A pass would support only an exact-output operator-level prefill/inference optimization for this pinned original GPT-2 FP32 CPU workload and runtime. It would not establish other architectures, other model families, Windows/ARM transfer, production serving, energy efficiency, training-held-out generalization, cognition, intelligence, scientific/model acceptance or native Wingless/Yggdrasil capability.

Keep research-only and DRAFT/UNMERGED. Preserve all G71–G91 results, NO-GO decisions and blocked receipts unchanged. No protected-main change, deployment, controller/queue mutation, paid API, broker, model training or promotion is authorized.
