# CPU GPT-2 G90 — independent-request batching and CPU throughput

**Prospective preregistration — 2026-10-31.** This contract is committed before the G90 benchmark implementation, tests, workflow or measurement. Research-only inference systems work, separate from GPU ACC, FORGE autonomy/controller responsibilities, and native Wingless/Yggdrasil research.

## Hypothesis

Determine whether batching independent original GPT-2 requests improves aggregate CPU token throughput under a fixed three-logical-CPU budget, while preserving exactly the same greedy response per request.

This is not a claim of lower single-request latency. Batching explicitly trades individual request completion latency and memory for aggregate throughput. Report both; do not describe throughput gain as a latency gain.

## Frozen model/data/source identities

- Qualified G70 CPU source baseline: `20a540d0241519e2e9d90ace868ffd6db60bd065`; G54–G70 source trees unchanged.
- Original pretrained `openai-community/gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`, safetensors SHA-256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`.
- Original MIT GSM8K test source commit `3101c7d5072418e28b9008a6636bde82a006892c`, raw SHA-256 `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`.
- Reuse the exact G82–G89 SHA-ranking algorithm/seed `G68-GPT2-HELDOUT-20261030:`; use new disjoint source question ranks **204–215 inclusive**. Verify G68/G70 partition contracts and no overlap with earlier G82–G89 selected ranks. Exactly 12 original questions; no replacement or post-result reselect.
- Original G55 shared prefix; first 64 question token IDs; full FP32 weights unchanged; greedy argmax; exactly 8 newly generated tokens. No training, quantization, weight conversion, prepacking, compilation or speculative decoding.

## Fixed runtime and compared arms

- Native Ubuntu 24.04 x86_64, Python 3.11, PyTorch `2.5.1+cpu`, Transformers `4.48.3`, huggingface-hub `0.30.2`, safetensors `0.5.3`, tokenizers `0.21.1`, psutil `7.1.3`; verify exact versions, `torch.version.cuda is None`, and `pip check`.
- Pin the process to the same three logical CPU cores for all arms; PyTorch intra-op threads 2 and inter-op threads 1. Read back and record.
- All model inputs remain original and independent. Batch candidates are left-padded to the longest prompt in each group. Attention masks must hide all padding. Explicit position IDs are derived from cumulative non-padding mask counts, so each request receives the same original token positions as its independent batch-one execution. Extend each request's mask by one valid token at every decode step. No cross-request information flow or state sharing.
- Verify original model weights immutable; verify each request's input token sequence and output exactly match batch-one baseline. All arms use the same model forward, KV-cache semantics, full eight-token greedy decode and CPU thread budget.
- Arms: `batch1` sequential independent requests (baseline); and `batch2`, `batch4`, `batch8`, `batch12` independent-request groups. For each repetition, run the whole 12-request cohort exactly once per arm, split into deterministic groups, and rotate/reverse candidate arm order. No request is dropped or duplicated.
- Exactly 12 prompts × 4 repetitions × 5 arms = 240 complete request responses, 1,920 generated tokens; 48 independent full-response measurements per arm. Measure each arm's full 12-request cohort wall time and process CPU time; record batch group completion times and maximum sampled RSS. Include collation/padding in candidate arm wall time; prompt retrieval/tokenization and model load are reported separately, identical outside timing.
- Aggregate throughput is total original response tokens divided by full-cohort wall time. Also report requests/sec, per-request completion time distribution (the batch that completes a request), p95 group completion latency, worst paired per-request completion latency, total process CPU per generated token, and peak sampled RSS. Clearly distinguish batch-group completion from individual end-user response latency.
- Exact token parity is checked for all requests on every repetition. Counterbalance arm order and batch membership deterministically; no outlier deletion.

## Frozen acceptance

A batch size (bin\{2,4,8,12\}) is a throughput candidate only when all hold:

1. Frozen source/model/data identity, disjoint question ranks, native CPU, exact CPU affinity/thread settings and 48 full cohort repetitions per arm.
2. Every per-request generated token ID across all repetitions is exactly identical to that request's batch1 baseline.
3. Aggregate original-token throughput improves by at least **1.20×** versus batch1.
4. p95 batch-group completion latency ratio versus batch1 p95 individual-request latency is at most **2.00×**.
5. Maximum sampled RSS ratio versus batch1 is at most **1.50×**.
6. Process CPU time per generated token ratio versus batch1 is at most **1.50×**.
7. No NaNs, invalid masks/positions, batch contamination, missing responses, context overflow or non-deterministic output.

`BATCHING_PASS` if at least one frozen batch size qualifies. Select the qualifying size with maximum aggregate throughput; ties resolve to the smaller size. If no size qualifies, `BATCHING_NO_GO`. Token mismatch is `FAIL_EXACTNESS`; runtime/source/incomplete-cohort errors are `BLOCKED_ENV` / `BLOCKED_IMPLEMENTATION`. No thresholds or batch sizes may be added/removed after the experiment begins.

## Interpretation and authority

A pass establishes only an aggregate CPU inference throughput/latency/memory tradeoff for this pinned GPT-2 runtime, host, cohort and fixed CPU budget. It does not establish per-request latency reduction, another model family, other CPU architectures, production serving, energy efficiency, intelligence, scientific/model acceptance, or native Wingless/Yggdrasil capability.

Keep DRAFT/UNMERGED. Preserve all prior G71–G89 results unchanged, including every NO-GO and blocked feasibility receipt. No protected-main changes, controller/queue actions, deployment, paid API, broker activity, model promotion or Wingless/Yggdrasil source mutation are authorized.
