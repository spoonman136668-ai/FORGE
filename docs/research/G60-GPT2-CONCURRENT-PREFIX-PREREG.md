# G60 — Frozen concurrent GPT-2 prefix reuse and process-memory observation

**Research-only. Do not merge, promote, activate FORGE autonomy, use paid APIs or change scientific first-use.**

## Frozen basis
- Authentic source model: openai-community/gpt2 commit 607a30d783dfa663caf39e06633721c8d4cfcd7e; model.safetensors SHA256 248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707.
- Same single model and tokenizer pinned as G59. Retain G51–G59 code unmodified.
- PyTorch 2.5.1+cpu, transformers 4.48.3; one CPU intra-op thread; two concurrent request workers using ThreadPoolExecutor and a per-wave barrier; model in inference/eval mode, complete 16-token greedy incremental KV decoding.
- **Three policies**: no retained prefix cache, G59 second-seen LRU admission, G59 adaptive admission. All cache keys are exact token sequences; max two retained families. Admission/prefill/eviction takes place in coordinator in frozen *arrival order* per wave, before two parallel decode workers are released. Prefill cost is charged to the timed workload, not omitted.
- **Three frozen six-request streams**: high_locality=[0,0,0,0,1,1]; unique_only=[0,1,2,3,4,5]; thrash=[0,1,2,0,1,2], two requests per wave, three waves. Workload already pretokenized, distinct family prefixes and request-specific suffixes as G59; exact input identifiers recorded.
- **Pressure condition**: external hard cap of two retained prefixes and 42,000,000 retained K/V tensor bytes, with mandatory admission refusal and/or LRU eviction if a real KV cache would exceed budget. This is a real *cache allocation budget* enforced during inference, not synthetic OS memory exhaustion. No claim of OS swapping/production memory pressure.
- Entire run charges prefix prefill, data copying, cache hits/misses, eviction and all decoder executions. Three timed rotated paired trials per workload after untimed correctness and warmup. Preserve latency for every request, whole workload wall and process CPU, total generated tokens, throughput tokens/sec, exact retained KV tensor bytes, sampled resident process RSS with 10ms monitoring during each timed arm, and peak snapshots; RSS sampling is not exact high-water, so do not call it peak RSS.
- Strict correctness: all generated tokens and SHA per request must exactly match original no-cache reference; count and capacity invariants; true two-worker overlap per wave recorded by monotonic start/end timestamps; failures remain failures.
- Preregistered **screen only**: high-locality median adaptive speedup >=1.10×; unique-only median adaptive speedup >=0.95×; no exact-token mismatch or cache budget breach. Thrash and second-seen relative performance are reported with no cherry-picked acceptance. Distinguish engineering correctness from throughput and memory comparisons.
- This is **not** production concurrent HTTP serving, GPU, batched attention, dynamic paged KV, energy, multi-host or native Wingless/Yggdrasil model training. Do not claim universal acceleration. Existing G56 no-reuse slowdown, G58 thrash negative and G59 alternating second-seen advantage remain authoritative.
- The separate ACC G60 RTX GPU research PR #1260 is a distinct line. Do not combine its CUDA metrics with this CPU concurrency screen.
- Final exact-source Linux/Windows qualification required, publish all evidence in existing draft PR #1250. Initial gate failure, if any, is not silently overwritten.

**This contract must be committed separately before G60 executable or workflow.** Any changed thresholds after observations require a new gate.
