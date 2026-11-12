# G58 — Frozen authentic GPT-2 selective cache admission and eviction

Research-only; no first-use, FORGE controller change, accepted-source promotion, or production inference claim.

## Immutable inputs and controls
- Source: original G55 openai-community/gpt2 commit 607a30d783dfa663caf39e06633721c8d4cfcd7e, model.safetensors SHA-256 248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707.
- 1 CPU thread, torch 2.5.1+cpu, transformers 4.48.3, tokenizer and stage from G55; same common prefix plus eight unique family markers; distinct request suffixes; 16 greedy tokens per request.
- Frozen streams: high_locality_75pct=[0,0,0,0,1,1,1,1]; unique_0pct=[0,1,2,3,4,5,6,7]; thrash_four_families=[0,1,2,0,1,2,3,3]. Unique prefix identities checked; no post-hoc sequence changes.
- Three arms: no cache, eager admit on every miss with LRU cap 2, selective admit only from second observation of exact-prefix tokens with LRU cap 2. The first selective miss decodes full prompt without cached prefill. On second sighting compute prefix and retain for later hits.
- Untimed correctness/warmup, then five paired whole-eight-request rotations and alternating order. Charge misses, prefill, eviction, cache copy and decode. Report process CPU, wall, cache bytes (sum of K/V tensors), LRU size and evictions, OS RSS snapshots (not true OS peak).
- Correctness: all generated tokens equal across policies and repetitions, no false hits, cap <=2, zero selective admissions and memory for unique-only stream, six eager evictions on unique stream.
- Predeclared screen: median selective high-locality speedup >=1.15x AND median selective unique-only speedup >=0.98x versus baseline. FAIL must be preserved; no threshold tuning on observed data.
- Thrashing/eviction outcome is separately descriptive, without cherry-picking a universal win.
- Independent production acceleration UNVERIFIED. No native Wingless/Yggdrasil model, batching, concurrency, GPU, energy, true peak RSS, startup or tokenization in paired timings.
- Preserve G56 original observed 0.9495x no-reuse eager negative unchanged.
- Preserve original G57 byte-identical G51 code/results unchanged. Full Linux/Windows source regression required at exact resulting commit. DRAFT/UNMERGED.

First frozen executable implementation commit: 60bf091ee5f72572cc29463dd149db4d0c25401b. A changed experiment requires a separately named future gate.
