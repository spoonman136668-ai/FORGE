# CPU G97 — overflow-aware cache bypass preregistration (development only)

Status: PROPOSED; no measurements or acceptance. Parent: FORGE PR #1349 at a5473a06cfd36123ad3eb131a0b1be593b9867e6. G96 DEVELOPMENT_NO_GO is preserved; G93/G94 remain separately bounded positives, G95 NO_GO.

## Question and falsifiable hypothesis
Can a deterministic, bounded, online-only working-set overflow detector bypass cache residency and avoid unnecessary KV cloning/building without worsening recurrent-prefix workloads? Null: no candidate passes all predeclared criteria in every required stratum.

## Design
Compare no-cache, G96 LRU/second-use/frequency/cost-aware as frozen controls, and one new overflow-bypass candidate. Candidate observes only past exact-prefix keys, hits/misses and bounded online counters; never future requests, test labels, hidden holdout or prompt-derived answers. Use a fixed window of 16 preceding requests and an overflow state when distinct keys exceed capacity 4 and window hit fraction is below 1/8. While in overflow state, bypass KV build/residency for unseen keys; preserve hits for existing resident keys. Exit only after 16 further requests with at most 4 distinct keys; no future lookahead. Cold start uses existing LRU behavior. State transitions and overhead are charged to candidate. The initial thresholds are hypotheses, not tuned from G96 overflow results.

## Controls and invariants
Identical pinned GPT-2 FP32 weights/tokenizer, exact generated tokens, 2 intra-op/1 inter-op threads, 3-core affinity, generation parameters, prompt streams, 4 entries and 86,114,304-byte KV residency ceiling. All cached KV must remain immutable and request-local copies must not alias. Keep no-cache and frozen G96 arms unchanged. Track wall/CPU/p95/RSS, minimum paired speedup, throughput, hits, misses, evictions, bypasses, clones, prefill, resident bytes, decision overhead, and state transitions.

## Data separation
Use only existing G96 development ranks 276–287 for implementation debugging, never protected ranks 288–299. Freeze a new independent development stream manifest and SHA-256 before measuring. No protected holdout, model selection or production integration. Do not claim independent scientific validation from reused development sources.

## Frozen evaluation criteria
Every required stratum (round-robin, bursty, mixed, overflow) must retain exact parity and capacity/byte limits, median throughput ratio >=1.15, minimum paired speedup >=0.90, p95 latency ratio <=1.10, total CPU ratio <=1.10 and maximum sampled RSS ratio <=1.15 against no-cache. Four paired repetitions per stratum with deterministic seed, equal generated-token counts, and full request accounting. Report per-stratum verdicts; any failure is NO_GO. The overflow candidate must additionally reduce overflow wall time against frozen G96 LRU, with no relaxation of the no-cache-relative thresholds.

## Sequence and authority
1. Verify source identities and development manifest; implement isolated policy and adversarial tests for transition hysteresis, oversized KV, build failures, determinism, exact-key isolation and bounds.
2. Obtain focused tests and original Linux/Windows regression at exact new head; distinguish infra from test failure.
3. Execute development-only paired original-model measurements; publish raw artifacts, hashes, source identity and per-stratum verdict.
4. Freeze a new independent holdout and seek separately authorized scientific first-use only if development criteria pass.
No controller, scheduler, model service, paid API, protected cohort, merge, or runtime activation is authorized by this document.
