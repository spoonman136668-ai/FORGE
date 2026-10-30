# G61 — Preregistered concurrency-loss attribution (diagnostic only)

**Scope: G60 follow-on in existing draft FORGE PR #1250. Source/hosted research only. No deployment, model acceptance, F139/controller/queue interaction, paid API or scientific first-use.**

## Frozen identities
- Starting G60 result at `6e7fc9be5c381092c3989afb3d75d6c05ef87644`: authentic concurrent high-reuse adaptive 0.903500105110561x (FAIL versus >=1.10x), unique 1.0022110118398422x and thrash 1.0385029900337663x. Preserve these as independently qualified negative/neutral results without changing their source code.
- Original authentic `openai-community/gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`, model.safetensors SHA256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`. Same PyTorch 2.5.1+cpu, transformers 4.48.3, one intra-op CPU thread as G60, model in eval/inference.
- Frozen G60 tokenized prompt protocol: original G55 common prefix + ` Family i has a unique context marker.`, suffix ` Request j: state the bounded validation requirement.`, 16 greedy tokens/request.
- No modifications to G51–G60 sources, no threshold modifications, no merge or accepted-science promotion.

## Attribution screen, frozen before implementation
- Workloads: `high_locality=(0,0,0,0,1,1)` and `unique_only=(0,1,2,3,4,5)`; six requests, same suffix per request and no future-peeking.
- Policies: original G59 no-cache, second-seen LRU and adaptive admission with exact-prefix identity, capacity two, 42,000,000 retained KV bytes. Coordinator charges all prefix prefill, admission, eviction, and request preparation during timed period.
- Worker comparison: actual one-worker serial decoding versus two-worker ThreadPoolExecutor *overlapped forward* with barrier synchronized request pairs; two timed rotated/alternating paired repetitions each, after correctness check and one untimed warmup each.
- Instrument independently: coordinator prefill, worker deep copy of cached KV, first model forward, remaining 15 incremental model forwards, worker dispatch/wait, end-to-end wall time, process CPU, request latency, tokens/second, retained KV peak-by-request and sampled process RSS with 10ms polling. Phase sums are not exclusive critical-path time due concurrency/overlap.
- Exact output token parity required across every arm, concurrency setting and repetition to original no-cache one-worker reference. Assert overlap in every two-worker wave, cache counts and retained tensor bounds.
- Report CPU wall/CPU ratios and differences, negative and positive evidence without selecting only winning workloads. Separate phase breakdown per request, aggregate per wave and per arm. No automatic performance PASS criterion (diagnostic only).
- Falsifiable attribution: prefill and copy charges >zero; if high-locality two-worker speedup remains <1x while serial >1x, concurrency-sensitive regression reproduced. Quantify copy/prefill/forward phase contributions but do **not** claim unique causality from correlated timings.
- Host/limits: one GitHub Linux CPU runner, same one frozen checkpoint, no real HTTP serving, production scheduler, GPU, batching, optimized serving engine, OS swapping, energy, or exact peak RSS. No claim of native Wingless/Yggdrasil architecture improvement.
- Initial or diagnostic failures must be retained. G60 latest exact-head full Linux/Windows regression was pending at preregistration time; check separately at G61 closure.

Freeze this written contract as its own commit **before implementation or first run**. A follow-up optimization is a separately named gate; don't tune G61 instrumentation to produce acceleration.