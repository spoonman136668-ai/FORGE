# CPU GPT-2 G91 — length-aware grouping for independent-request CPU batching

**Prospective preregistration — 2026-10-31.** Committed before G91 executable source, tests, workflow or measurement. This is CPU LLM execution research and is separate from ACC G91 (the separate acceleration-screen series), FORGE autonomy/controller work, GPU ACC and native Wingless/Yggdrasil research.

## Motivation and hypothesis

G90 showed fixed-size independent-request batching was not useful on the pinned three-CPU GPT-2 host: batch2 throughput was only 1.0235× batch1 and missed the frozen 1.20× threshold; batches 4/8/12 were slower. G90's group formation was schedule-based and did not bucket prompts by tokenized context length.

G91 tests one distinct, narrow intervention: group similarly sized original prompts together, reducing left-padding waste and unnecessary padded attention computation in each batch. It does not change batch capacity, model, weights, precision, attention backend, tokenizer, greedy decoding or CPU budget. A length-sorted scheduler is only useful if it yields a measurable end-to-end improvement after charging sorting/group construction.

## Immutable identity and disjoint cohort

- Qualified G70 baseline: `20a540d0241519e2e9d90ace868ffd6db60bd065`; G54–G70 source trees must remain byte-identical.
- Original pretrained `openai-community/gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`, safetensors SHA-256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`.
- Original MIT GSM8K test source commit `3101c7d5072418e28b9008a6636bde82a006892c`, raw SHA-256 `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`.
- Exact G82–G90 SHA-ranking algorithm and seed `G68-GPT2-HELDOUT-20261030:`. Use original ranks **216–227 inclusive**; verify G68/G70 partition contract and disjointness from all prior screen intervals, including G90 ranks 204–215. No question reuse, replacement or post-result reselect.
- Preserve G55 original prefix, first 64 question-token IDs, full FP32 model weights, greedy argmax, KV-cache semantics and eight new tokens. No training, quantization, compilation, prepacking or model transformation.

## Fixed runtime and arms

- Native Ubuntu 24.04 x86_64; Python 3.11; PyTorch `2.5.1+cpu`; Transformers `4.48.3`; huggingface-hub `0.30.2`; safetensors `0.5.3`; tokenizers `0.21.1`; psutil `7.1.3`. Verify versions, `torch.version.cuda is None`, and `pip check`. Preserve actual `pip freeze` and runtime metadata.
- Same three logical CPU affinity for all arms; intra-op threads 2, inter-op threads 1. Read back and record.
- Five arms, same twelve original prompts:
  1. `batch1`: batch-size-one independent baseline.
  2. `batch2_random`: batches of two with deterministic shuffled membership.
  3. `batch2_length`: batches of two after stable ascending input-token-length sort.
  4. `batch4_random`: batches of four with deterministic shuffled membership.
  5. `batch4_length`: batches of four after stable ascending input-token-length sort.
- Length is measured after original G55 prefix concatenation and the original first-64-question-token truncation. No prompt shortening. Length-sort/group construction and left-padding collation are included in candidate full-cohort wall time. Batch1 tokenization/load is performed once, outside timing and reported separately; candidate scheduler receives already-computed lengths/tensors but sorting time is charged.
- Left padding, attention masks and position IDs follow G90: positions derive from cumulative non-padding mask values; every request must retain identical token positions/output independent of batch membership. All arms use original cached greedy decoding and eight response tokens.
- Each arm processes all twelve requests once per repetition; four repetitions; five arms; **240 authentic full responses and 1,920 generated tokens**. Record all per-request input lengths, group membership, per-group padding-token count, full-cohort wall and process CPU time, group completion latencies, sampled RSS, per-request output hashes and exact settings.
- Counterbalance arm order deterministically; random-membership controls are regenerated from a frozen schedule seed per repetition. For length buckets, stable tie-breaker is source rank/index. Never drop a request or change a group after seeing performance.
- Verify output token IDs for every question are identical to its batch1 result on all four repetitions and all groupings. No outlier deletion.

## Frozen acceptance

A length-aware candidate qualifies only if all conditions hold:

1. Frozen source/model/dataset/rank identity, CPU runtime/affinity, full cohort and four repetitions per arm.
2. Exact greedy token parity for all 240 full responses and 1,920 generated tokens.
3. Actual candidate full-cohort token throughput at least **1.20×** batch1.
4. Candidate p95 group-completion latency divided by batch1 p95 individual-request latency at most **2.00×**.
5. Maximum sampled RSS ratio versus batch1 at most **1.50×**.
6. Process CPU time per generated token ratio versus batch1 at most **1.50×**.
7. No invalid masks/positions, duplicated/missing requests, context overflow, or cross-request contamination.

A length-aware batch arm must also outperform the corresponding random-membership arm in aggregate throughput; otherwise any observed batch speedup cannot be attributed to length bucketing. `LENGTH_BUCKET_PASS` if at least one length-aware arm meets all absolute thresholds and beats its same-size random control. Select maximum qualifying throughput; ties resolve to smaller batch size. Otherwise `LENGTH_BUCKET_NO_GO`. Token mismatch is `FAIL_EXACTNESS`; missing data/runtime identity is `BLOCKED_ENV` or `BLOCKED_IMPLEMENTATION`. Thresholds, arm list, cohort and scoring may not change after measurement begins.

## Interpretation and authority

A pass is only an aggregate CPU inference scheduling result for this pinned GPT-2/runtime/host/cohort. It is not a single-request latency reduction, production-serving validation, other-model/architecture transfer, energy result, intelligence claim, native Wingless/Yggdrasil result or scientific acceptance.

Keep DRAFT/UNMERGED. Preserve G71–G90 results unchanged, including all NO-GO and blocked receipts. No protected-main changes, controller/queue mutation, deployment, paid API, broker, model promotion or Wingless/Yggdrasil source mutation is authorized.
