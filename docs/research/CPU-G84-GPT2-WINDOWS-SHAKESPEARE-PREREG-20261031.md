# CPU GPT-2 G84 — Windows-native original-model Shakespeare policy replication

**Prospectively frozen before executable source and model measurement, 2026-10-31.** This is the Windows-host replication gate for the separate CPU GPT-2 LLM Evaluation stream. It is not RTX GPU ACC, not a new model or inference algorithm, not Wingless/Yggdrasil science, and not production acceptance.

## Provenance and baseline

- Exact unchanged qualified CPU G70 foundation: `20a540d0241519e2e9d90ace868ffd6db60bd065` (branch `research/llm-g54-gpt2-pinned-20261030`). G54–G70 sources and accepted baselines must remain byte-identical.
- G82 same-family GSM8K replication PASS remains separately recorded; its final Linux/Windows source regression passed. G83 original Shakespeare workload benchmark is an authentic **TRANSFER_FAIL** because uniform2 vs uniform1 reached 1.327414651× against the frozen ≥1.35× floor. G83's result is not revised by G84.
- This prereg is an independent immutable commit and MUST exist before any G84 executable, test or workflow source is committed.

## Question and fixed study

Does the previously selected uniform-two-thread policy reproduce its original-model CPU performance advantage on a native Windows host under a fixed and equal resource budget, compared with the original GPT-2 one- and three-thread controls?

Use the unchanged original pretrained `openai-community/gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`, verify original safetensors SHA256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`, and use the exact original Karpathy char-rnn Tiny Shakespeare source commit `370cbcd448eb7daf32f21a6be560b70e0b33c4e3`, 1,115,394 bytes, SHA256 `86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed`. Do not substitute another corpus, synthetic prompts, model checkpoint, tokenizer, dtype or runtime.

Deterministically select the same 12 non-overlapping 2,048-codepoint spans from the final 10% of the verified original corpus, with stride 3,072 and the first 96 original GPT-2 token IDs of each. Produce exactly eight greedy original-model tokens for each request. No weights or model architecture changes, no cache reuse between requests, no post-result tuning.

## Windows execution and matched resource controls

- Execute the original full-decode benchmark only on a native `windows-latest` GitHub Actions host. Require `os.name == "nt"`; fail closed otherwise.
- Pin CPython 3.11, `torch==2.5.1+cpu`, `transformers==4.48.3`, `huggingface_hub==0.30.2`, `safetensors==0.5.3`, `tokenizers==0.21.1`, and `psutil==7.1.3`; run `pip check` and retain the environment inventory.
- Fix the process affinity to exactly the first two available logical CPUs, require at least two, and use one PyTorch inter-op thread. The same two-CPU affinity applies to every arm. If two-CPU affinity is unsupported, classify as BLOCKED_ENV rather than quietly changing the budget.
- Compare original unmodified FP32 GPT-2 full eight-token requests with three controls: `uniform1` (one intra-op thread), preselected `uniform2` (two), and `uniform3` (three). The three-thread control is intentionally retained under the same two-CPU process affinity; any oversubscription is part of this fixed, matched resource condition, not grounds to alter the control. Set the thread count inside each timed request so thread-pool switching overhead is included symmetrically.
- Exactly 12 spans × 5 counterbalanced/rotated repetitions × 3 arms = 180 timed original responses and 1,440 generated tokens. Require 180/180 full eight-token greedy output identity across arms and repetitions for each prompt. Record source/prompt/output hashes, exact CPU affinity and Windows/CPU environment, per-arm latency, p95, process CPU time, sampled RSS, and immutable result artifact hashes. No outlier deletion.

## Frozen transfer thresholds — unchanged from G83

G84 is a separate Windows replication, not a redefinition of G83. Declare `WINDOWS_TRANSFER_PASS` only if every condition holds:

- Median uniform2 speedup versus uniform1 ≥ 1.35×.
- Median uniform2 speedup versus uniform3 ≥ 1.05×.
- Minimum paired uniform3/uniform2 speed ratio ≥ 0.90×.
- Uniform2/uniform3 p95 latency ratio ≤ 1.10×.
- Sampled maximum RSS ratio (uniform2/uniform3) ≤ 1.10×.
- Total process CPU-time ratio (uniform2/uniform3) ≤ 1.25×.
- Original source/model identities, fixed resource budget, complete trial count and exact-token parity all pass.

Otherwise record `WINDOWS_TRANSFER_FAIL`; source or environment identity failure is `BLOCKED_ENV`; any output mismatch is a correctness failure. No threshold changes, adaptive settings, or post-hoc explanations can convert a failure into a pass.

## Interpretation and limits

A pass would establish only that this already-selected CPU thread policy replicates under this Windows host/resource configuration on this particular input family. It does not establish a second CPU architecture, model-unseen evaluation data, language quality, cognitive/intelligence generalization, a novel algorithmic improvement, native Wingless/Yggdrasil capability, or production inference readiness. G83 remains TRANSFER_FAIL regardless of G84.

Even a Windows pass leaves a second independent CPU architecture and full scientific/model acceptance UNVERIFIED. No model integration, scientific admission, promotion, deployment, protected-main change, controller/queue mutation, paid API, broker access, or native Wingless/Yggdrasil source mutation is authorized by this study. Keep the work research-only and DRAFT/UNMERGED.