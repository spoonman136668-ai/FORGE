# G65 — Frozen shared-forward-pool prefill slot release, original GPT-2 CPU

**Status:** Pre-execution research contract. Existing draft FORGE PR #1250; no controller, autonomy, accepted source, native Wingless/Yggdrasil model, deployment, paid API, promotion, or scientific first-use authority.

## Prior evidence and immutable identity

- G64 source at `70a9d31f41333afe9fb958e11773f9ddbf406246`; authentic execution run `41042734907`: frozen engineering PASS and acceleration **FAIL**. Full exact-source Linux and Windows CI run `41042741623`: **PASS**. G64 conditional route high-locality B=3 only `0.9021036129158317×` versus no cache and `0.7852548378684276×` versus serialized; unique/thrash near neutral. Preserve all original G56–G64 negative results unmodified.
- Authentic checkpoint: `openai-community/gpt2` at commit `607a30d783dfa663caf39e06633721c8d4cfcd7e`, `model.safetensors` SHA256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`. Original G55 tokenizer and public prompt strings, PyTorch 2.5.1+cpu, Transformers 4.48.3, one torch intra-/interop thread. Verify every model file through original G55 staging.
- Do not edit any G51–G64 original experiment or protocol source. Commit this document separately before executable G65 code or any measurements.

## Controlled resource and workload design

- Pin real process CPU affinity separately to exactly **B=2 or B=3** allowed logical CPUs, recorded per trial. Every arm restricted to at most **B total** concurrently running forward tasks (decode or prefix prefill). Candidate must not create a hidden extra forward worker or use spin/sleep.
- Frozen G64 arrival waves: high-locality `[0,0,0,0,1,1]`, all-unique `[0,1,2,3,4,5]`, thrash `[0,1,2,0,1,2]`; six pretokenized requests and 16 greedy output tokens/request. Waves of **B arrivals**, complete each wave before advancing. Wave-specific route is causal G64 rule (current family must have appeared twice in previous completed waves), no future traffic or answer peeking. High-locality expected active waves: B2 off/on/off, B3 off/on; unique/thrash off throughout.
- Four tested arms:
  1. `no_cache` — B decoder worker pool, no cross-request prefix storage.
  2. `serialized_prefill` — B decoders, G59 adaptive causal admission, serial coordinator prefix preparation before decode.
  3. `fixed_reserved` — G64-style causal conditional route. Active wave reserves one dedicated prefill worker and B−1 decoder workers **for entire active wave**; inactive uses all B decoders and no prefix KV storage.
  4. `shared_forward_pool` — identical G64 causal routing and G59 adaptive cache admission but uses **one B-slot task pool** for all forward tasks. When active, a missing eligible prefix producer is enqueued before any decoder that depends on it. Once the prefix-producing task completes, its pool slot immediately becomes available to queued decoders in that same wave. No permanently reserved prefill slot. Exactly one producer per resident prefix and future sharing. Inactive waves use B decoders, no stored KV. Pool creation, scheduling, future waiting, eviction, and teardown charged to all arms.
- Prefix keys are exact original model tokenizer IDs, G59 adaptive history only; cap 2 retained prefix entries and 42,000,000 retained float32 KV bytes. Deep-copy shared prefix KV for every decoder request; first cache miss with no admission decodes full prompt. Use frozen G64 prefill bytes calculation and verify actual tensors match.
- Enforce no forward-task starvation/deadlock: never schedule dependent decode before its prefix producer. Detect and FAIL on unfulfilled producers, duplicate producers for in-flight key, token mismatch, exceeding worker/CPU budget, false hits, or wrong route decisions.
- **Two counterbalanced paired repetitions per arm/cohort/budget** after independent untimed exact-token parity and warmup. Charge every request's entire wave, including pool setup, cache work, prefill, copy, future wait and complete 16-token decoder. Record whole-workload elapsed and CPU time, throughput, sampled RSS (10ms, NOT exact peak), retained KV bytes, per-wave forward-task start/end intervals and max observed concurrent model tasks, pool wait, producer count, hit/miss/admission/eviction, expected active routes and per-request output digests.
- Original source and runner controls must be mechanically verified before model execution; final Linux and Windows regression on the G65 exact final SHA mandatory.

## Preregistered positive *engineering screen only*

- Correctness requires identical 16-token outputs for every arm/cohort/budget/trial and all routing, model-identity, CPU affinity, prefix capacity, worker-count, and single-producer invariants. All control arms must use the same arrival waves.
- Performance **PASS only if all**: high-locality B3 shared/no-cache median >=1.05x, high-locality B3 shared/fixed_reserved median >=1.05x, high-locality B2 shared/no-cache >=0.98x, unique B3 shared/no-cache >=0.98x, thrash B3 shared/no-cache >=0.98x. Report full matrix, including negatives, without threshold tuning.
- Require source-observed prefix preparation overlap with an unrelated decoding forward in at least one active-wave trial; independently record whether released slot executes a queued decoder before that wave completes. If this mechanism is **not observed**, engineering screen FAIL regardless of speedup.
- Even PASS would be only a bounded single-host, synthetic-wave, CPU-affinity engineering screen. No optimized production serving, dynamic continuous batching, GPU, energy, cross-host independent replication, real OS-memory pressure, or native-model transfer is tested; science/production acceptance remains **NOT GRANTED** and PR stays **DRAFT/UNMERGED**.

**This exact contract must be committed on the research branch before any G65 benchmark code.**