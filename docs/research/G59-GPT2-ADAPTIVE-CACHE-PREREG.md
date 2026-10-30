# G59 — Pre-execution frozen adaptive-prefix admission protocol

**Classification: independent engineering screen only; no FORGE acceptance, training, runtime, queue, deployment, scientific first-use, or production-serving inference.**

## Provenance and benchmark identity
- Original GPT-2 `openai-community/gpt2` commit `607a30d783dfa663caf39e06633721c8d4cfcd7e`, `model.safetensors` SHA256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`; reuse pinned read-only G55 model staging and tokenizer.
- CPU PyTorch 2.5.1+cpu, Transformers 4.48.3, single-thread, identical 16-token greedy generation (manual incremental KV cache) across arms. Eight pretokenized requests per stream, warmed comparison, exactly three paired/rotated execution trials per stream.
- Preserve G58 original source and its negative results exactly. Use separate new source and workflow, draft PR #1250, no new PR or model integration.

## Frozen policies
- No cache: decode each full prompt with normal per-request KV caching, retain no cross-request prefix.
- Second-seen LRU: first encounter has no prefix cache; on subsequent encounter, prefill prefix, retain in capacity-limited LRU; all future retained hits reuse the exact prefix.
- Adaptive LRU: on a cache miss, admit only if the current exact prefix was **immediately previous** OR it appeared **at least twice in the six prior requests**. First sighting never admits. No future request data, score labels, true future hit patterns or source-privileged oracle can influence decisions.
- All policies see the *same externally frozen per-request cache-entry budget* (0, 1 or 2). Evict LRU items before each request until within budget. No retained K/V at budget 0, even for existing prior entries. Capacity 2 max, never relax under pressure.
- Memory-pressure schedule is an **exogenous controlled budget simulation**, not a real OS pressure or concurrent-serving measurement. Cache bytes report retained tensor key/value bytes only, and sampled RSS is NOT peak RSS.

## Frozen streams and budgets
- `high_locality`: families `[0,0,0,0,1,1,1,1]`, capacity `[2,2,2,2,2,2,2,2]`.
- `unique_only`: `[0,1,2,3,4,5,6,7]`, capacity 2 throughout.
- `thrash_four`: `[0,1,2,0,1,2,3,3]`, capacity 2 throughout.
- `alternating`: `[0,1,0,1,0,1,0,1]`, capacity 2 throughout.
- `pressure_shift`: `[0,0,0,1,1,1,0,0]`, capacity `[2,2,1,1,0,0,1,1]`.
- Prefix identities are exact token sequences derived from frozen G55 public prompt plus one of eight `Family i` markers. Each request gets its own fixed request suffix.

## Precommitted decision, negatives, required evidence
- Every arm and every paired trial must have exact generated-token parity to no-cache for all eight requests, accounting for 16 tokens each; invalid/hallucinated cache hits or exceeded budget FAIL. Cross-arm exact digest recorded for each request.
- Three paired trials per stream, rotated/reversed order; charge all prefill, inference, eviction and cache-copy operations. Output wall and process CPU time per arm/trial, hit/miss/admission/eviction counts, retained KV bytes, RSS snapshots, workload hash, source SHA, dependency freeze and stage identity.
- Positive adaptive **screen only if all three** median paired whole-stream adaptive/baseline speedups hold: high locality ≥1.15×, unique-only ≥0.98×, thrash-four ≥0.97×; and complete token parity/capacity checks. Report pressure-shift and alternating results but do not select thresholds post-results.
- Explicit negatives remain: G56 0%-reuse eager slowdown 0.9495×; G58 thrashing selective slowdown 0.9649× and high-locality admission tradeoff. Do not replace evidence by G59 synthetic policy outcomes.
- No claim of speedups over optimally batched or concurrent serving, GPU, optimized inference engines, energy, peak OS RSS, training, FORGE model development or cross-architecture transfer.
- No change to accepted refs, Mind-Palace scientific authority, original FORGE loops or external controller. Full Linux/Windows regression at final exact SHA required; GitHub-hosted research-only workflow may run concurrently without interaction with owner.

**Freeze timestamp by source commit:** this preregistration must be committed before executable G59 implementation and before benchmark runs. Any post-result tuning requires a distinctly identified successor, not editing this contract.
