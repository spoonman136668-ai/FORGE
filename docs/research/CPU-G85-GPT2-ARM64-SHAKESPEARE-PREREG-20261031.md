# CPU GPT-2 G85 — native Linux ARM64 original-model Shakespeare replication

**Frozen before executable source and model measurement, 2026-10-31.** Research-only continuation of the CPU GPT-2 LLM Evaluation stream. Separate from RTX GPU ACC, FORGE controller/autonomy, and native Wingless/Yggdrasil experiments.

## Question

Does the fixed two-thread CPU inference policy reproduce on a genuinely different processor architecture, native ARM64, using the same original model, source family, heldout input locations and strict controls used in G83?

This is the first hardware-architecture transfer attempt, not a new algorithm and not an intelligence result. G83's authentic x86_64 Shakespeare result remains **TRANSFER_FAIL** (uniform2 speedup 1.327414651× vs uniform1, below frozen 1.35×). G85 cannot repair or rewrite it.

## Frozen identities and source

- Unchanged qualified CPU G70 base: `20a540d0241519e2e9d90ace868ffd6db60bd065`.
- Original pretrained model: `openai-community/gpt2`, revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`, original safetensors SHA256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`; use existing pinned G55 seven-file staging and verify model identity before measurement.
- Exact original Karpathy char-rnn Tiny Shakespeare source commit `370cbcd448eb7daf32f21a6be560b70e0b33c4e3`, raw bytes 1,115,394, SHA256 `86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed`.
- Reuse G83's deterministic selection exactly: last 10% original Unicode text; 12 non-overlapping 2,048-codepoint spans at 3,072-codepoint stride; first 96 original GPT-2 token IDs per span; 8 original greedy output tokens. Require exact source/data/model hashes and preserve offsets, source-span hashes, input-token hashes and output hashes. Do not substitute datasets, prompt lengths, seeds, models, weights, dtype or tokenizers.
- Original model remains FP32 and evaluation-only; no training or weight changes. No model-serving network workload claim.

## Native ARM64 host and controlled resources

- Use the native `ubuntu-24.04-arm` GitHub-hosted runner, not emulation or x86_64. Require Linux POSIX and `platform.machine()` exactly `aarch64` or `arm64`; record CPU implementer/model, processor identity, OS/kernel, Python, PyTorch build, thread environment and logical-CPU inventory. If host architecture is not genuinely ARM64, fail closed.
- Pin CPython 3.11; PyTorch `2.5.1` from the official CPU wheel index `https://download.pytorch.org/whl/cpu`; Transformers `4.48.3`, huggingface_hub `0.30.2`, safetensors `0.5.3`, tokenizers `0.21.1`, psutil `7.1.3`. Confirm `torch.version.cuda is None`, exact package versions and `pip check`. ARM64 CPU wheel availability is verified against the official package index before freezing this plan.
- Restrict the benchmark process to exactly the first **three available logical CPUs**, identical count to G83's x86_64 experiment. Every thread arm sees the same affinity. Fix PyTorch inter-op threads to 1. Measure actual affinity and fail closed if it cannot be set/read back. All intra-op thread-setting overhead remains inside each measured request.
- Compare original `uniform1` (one thread), preselected `uniform2` (two threads) and `uniform3` (three threads) full original-model decode.
- Exactly 12 spans × 5 counterbalanced/rotated repetitions × 3 arms = 180 original timed responses, 1,440 generated tokens and 60 paired records. Strict full eight-token identity across all three arms and repetitions for each span. Record median/p95 latency, sampled RSS, process CPU time, environment, exact arm order, source fingerprints and all original samples. No outlier exclusion.

## Preregistered pass/fail — unchanged G83 cutoffs

Declare `ARM64_TRANSFER_PASS` only if all conditions hold:
- uniform2 median speedup vs uniform1 ≥ 1.35×;
- uniform2 median speedup vs uniform3 ≥ 1.05×;
- minimum paired uniform3/uniform2 speed ratio ≥ 0.90×;
- uniform2/uniform3 p95 ratio ≤ 1.10×;
- sampled maximum RSS ratio ≤ 1.10×;
- cumulative process CPU ratio ≤ 1.25×;
- exact source/model identity, true native ARM64 execution, fixed three-CPU budget, complete 60-pair / 180-response study and exact-token parity all pass.

Otherwise record `ARM64_TRANSFER_FAIL`; wrong architecture, unsupported runtime or source mismatch is `BLOCKED_ENV`; output mismatch is a correctness failure. No threshold changes or post-result tuning. Cross-host x86_64 vs ARM64 absolute timings are descriptive only; the within-host controls determine the frozen verdict.

## Interpretation / authority boundary

A pass would demonstrate only that the same CPU thread-count policy passes these frozen resource/performance controls on one native ARM64 host and this fixed Shakespeare input cohort. It does not prove model-unseen data, general language quality, learned intelligence, native Wingless/Yggdrasil capability, model integration, production inference readiness, or a new algorithmic win. It also does not revise G83's x86_64 TRANSFER_FAIL.

Keep research DRAFT/UNMERGED regardless of result. Scientific/model acceptance is NOT_GRANTED. No protected-main change, model promotion, deployment, controller/queue mutation, paid API, broker activity, or Wingless/Yggdrasil source mutation is authorized. This preregistration must have an immutable Git commit before any G85 executable source, tests or workflow are added.