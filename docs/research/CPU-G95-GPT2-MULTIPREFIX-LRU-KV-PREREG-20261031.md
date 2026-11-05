# CPU GPT-2 G95 — multi-prefix LRU KV cache under interleaved traffic

**Prospective preregistration — 2026-10-31.** Committed before G95 executable source, tests, workflow and measurement. CPU inference-systems engineering only; not GPU ACC, FORGE autonomy or native Wingless/Yggdrasil research.

## Motivation and hypothesis

G93 showed 2.329× throughput for one repeated shared prefix with twelve requests. G94 showed that this reuse remained useful across fixed cohort sizes 2, 4, 6 and 12, with 1.390× to 2.245× throughput gains. Neither study tested multiple prefix keys, a finite resident cache, interleaved requests, cache hits/misses or LRU eviction.

G95 tests a realistic cache-management boundary: four distinct exact instruction-prefix token sequences, three original questions assigned to each prefix, and a deterministic round-robin request stream that revisits all four keys. The candidate uses an LRU cache with capacities 1, 2 and 4 prefix entries. A miss builds and stores that prefix's KV state; a hit reuses it. Every request receives a deep copy of the cached KV state so request-specific suffix/decode cannot mutate the shared entry.

Hypothesis: a resident cache large enough to retain the active prefix working set materially improves end-to-end throughput and CPU cost even with interleaved multi-prefix traffic; undersized capacities expose thrashing and fail closed.

## Immutable identity and disjoint original cohort

- Qualified G70 baseline: `20a540d0241519e2e9d90ace868ffd6db60bd065`; G54–G70 source trees must remain byte-identical.
- Original pretrained `openai-community/gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`; safetensors SHA-256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`; FP32.
- Original MIT GSM8K test source commit `3101c7d5072418e28b9008a6636bde82a006892c`; raw SHA-256 `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`; expected 749,738 bytes.
- Reuse exact G68–G94 SHA-ranking/partition protocol and seed `G68-GPT2-HELDOUT-20261030:`; use the next disjoint original question ranks **264–275 inclusive**. Verify G68 and G70 partition functions. No overlap with prior G82–G94 question ranks, no replacement or post-result reselection.
- Exactly four prefix strings are frozen below. Each is repeated 12 times (same common-context pattern) to form a reusable instruction prefix; they are intentionally distinct token sequences, not claimed semantic equivalents. Each prefix owns three unique original GSM8K question suffixes. Questions are tokenized without special tokens; original suffix text/token IDs are unchanged.
  - P0 is the exact established G55 prefix: `You are an assistant evaluating computational reuse. Answer precisely using the shared requirements, preserving correctness and avoiding unsupported claims. ` repeated 12 times.
  - P1: `You are an assistant evaluating computational reuse. Use the shared criteria to answer accurately, be concise, and do not make unsupported claims. ` repeated 12 times.
  - P2: `You are an assistant assessing computational reuse. Follow the shared requirements carefully, preserve correctness, and distinguish evidence from assumptions. ` repeated 12 times.
  - P3: `You are an assistant reviewing computational reuse. Give a precise answer based on the shared rules and avoid claims that evidence does not support. ` repeated 12 times.
- Prefix identity key is SHA-256 over exact prefix input token IDs plus pinned model revision, weight digest, tokenizer revision/files, dtype, attention/cache semantics. Keys cannot alias on text-only similarity or prefix length.
- Original FP32 weights, tokenizer, CPU attention path, greedy argmax, KV-cache dtype and exactly eight generated tokens remain unchanged.

## Workload and cache arms

- Native Ubuntu 24.04 x86_64; Python 3.11; PyTorch `2.5.1+cpu`; Transformers `4.48.3`; huggingface-hub `0.30.2`; safetensors `0.5.3`; tokenizers `0.21.1`; psutil `7.1.3`; CUDA unavailable. Verify exact versions and `pip check`; preserve environment/host manifest.
- Fixed identical affinity of three logical CPUs; intra-op threads=2; inter-op threads=1; read back and record.
- Twelve unique original questions are assigned deterministically, three per prefix, in ranked order. Each request's full prompt is the exact concatenation of its selected prefix IDs plus original suffix IDs.
- The measured request stream contains four complete cycles (48 authentic requests). Within each cycle use a round-robin interleave: P0-question0, P1-question0, P2-question0, P3-question0, P0-question1, ... through P3-question2. The exact 48-record sequence is frozen and hashed before execution. This deliberately revisits each key only after the other three keys, exposing LRU eviction when capacity is below four.
- Arm A `no_prefix_cache`: execute full prefix+suffix prefill for every request, then independent eight-token greedy decode.
- Candidate arms `lru_capacity1`, `lru_capacity2`, `lru_capacity4`: persistent in-process LRU cache with exact capacity N prefix entries across the full 48-request stream. On a hit, update recency and deep-copy its KV state for that request. On a miss, compute the prefix KV once, insert it, evict the least-recently-used entry only when full, and deep-copy the newly created state for the current request. No mutable request KV may be stored back into or shared with a resident entry.
- Every lookup, hit/miss, insertion, eviction, prefix build, deep copy, suffix prefill and cached decode is inside measured cohort time/CPU. Candidate cache starts empty for each repetition; do not carry entries between repetitions. Record every request's prefix key, hit/miss, evicted key, cache occupancy, setup/copy/suffix/decode timings and output hash.
- Four paired repetitions per arm, deterministic arm-order rotation, same 48-request stream. Total **4 arms × 4 repetitions × 48 = 768 authentic full responses and 6,144 generated tokens**. All requests are original questions but repeated as the frozen four-cycle serving stream.
- Before timing, for each prefix/question pair compare full-prompt and prefix-cache+suffix first-token logits/argmax. During every repetition require all eight greedy token IDs exactly match the no-cache result for that exact prompt. No prompt reuse across distinct source rows; no output aggregation across different prompts.
- Report per-arm aggregate tokens/sec, requests/sec, total wall/CPU, p95 and worst request latency, prefix-build count, hit rate, eviction count, cache copies, sampled max RSS, peak resident KV bytes (measured from tensor storage, not estimated by number of entries), and full input/output/key identities. Profile/cache instrumentation must not change timed model paths.
- Candidate memory includes retained resident prefix KV tensors plus temporary per-request copies and normal model activations. Report retained KV bytes separately from sampled process RSS. No cache quantization, compression, disk spill or background cache cleaner.

## Frozen acceptance

A cache capacity qualifies only if every condition holds:

1. Exact pinned source/model/dataset/runtime, ranks 264–275, exact four prefix strings/token IDs and frozen 48-request interleaving, with all four repetitions complete.
2. Exact prefix-key binding to model/weights/tokenizer/dtype/cache semantics; cache capacity never exceeds its integer entry limit; observed eviction order follows LRU.
3. No cached KV tensor is mutated or shared with per-request state; candidate cache contents after each request equal their immutable insertion snapshots.
4. All 768 responses and 6,144 generated tokens have exact per-prompt token-ID parity with the uncached baseline; every first greedy token also matches.
5. Aggregate full-stream throughput speedup versus uncached baseline >= **1.15×**, including every miss/build/eviction/copy cost.
6. Minimum individual paired request speedup (charge each cache miss's full prefix-build cost to that request; hits pay lookup+copy) >= **0.90×**.
7. Candidate p95 full-request latency / uncached p95 <= **1.10×**.
8. Total process CPU time / uncached <= **1.10×**.
9. Maximum sampled RSS / uncached <= **1.15×**; retained resident KV bytes are also explicitly reported and must stay within the observed capacity-scaled budget (no hidden entries).

`MULTIPREFIX_LRU_PASS` if one or more cache capacities meet all conditions. Report all capacities and select the fastest qualifying capacity; ties choose the smaller. Otherwise `MULTIPREFIX_LRU_NO_GO`. Token mismatch, cache alias/mutation or incorrect eviction is `FAIL_EXACTNESS_OR_ISOLATION`. Missing identities or incomplete workload is `BLOCKED_ENV`/`BLOCKED_IMPLEMENTATION`. No thresholds, prefix strings, stream order, workload or cache capacities may change after measurement starts.

## Interpretation and authority

A pass supports only bounded in-process prefix KV reuse for these four exact prefix keys, this deterministic interleaved workload, pinned GPT-2/runtime/CPU host. It does not establish benefit for unrelated or one-off traffic, cold single requests, other models, production serving or other hardware. G93/G94 remain independently valid; G95 cannot rewrite their results.

Research-only, DRAFT/UNMERGED. No protected-main changes, deployment, controller/queue mutation, paid APIs, broker activity, model training or promotion. No Wingless/Yggdrasil source changes or intelligence/scientific-acceptance claims.
