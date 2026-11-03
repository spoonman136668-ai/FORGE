# CPU G100 — Deferred first-use admission: frozen development plan

Status: PREREGISTERED FOR DEVELOPMENT ONLY. No original-model G100 performance evidence, protected first-use authorization, acceptance, deployment, or scientific success is claimed.

Source parent: FORGE PR #1349, qualifying SHA `ebb9516f9437d1df862d71056dd6817eea980227`.
Qualification receipts: G97 focused workflow #41627312207 and mandatory Linux/Windows workflow #41627318682 both PASS at that exact SHA.
Historical G97 original GPT-2 development workflow #41610758450 at `274363b6df59e7730727621bbc64e7f0bf7a426c`: source admission and token parity PASS; scientific verdict DEVELOPMENT_NO_GO. Do not promote this old result to the current source identity.

## Falsifiable question

Does the single additional rule in `research/cpu_g97/g100_deferred_admission.py`—defer KV construction on a key's first-ever miss, with the existing G97 overflow logic retained thereafter—reduce wasted speculative prefill in overflow without violating the frozen minimum paired-request speed floor or exact token parity?

Null: the G100 candidate does not meet every performance, resource, and correctness criterion simultaneously. Model-free replay and the passing focused tests are implementation evidence only, not speedup evidence.

## Isolation, controls and scope

Run a development-only original GPT-2 FP32 comparison of **no-cache**, unmodified G96 LRU, unmodified G97 overflow-bypass, and G100 deferred first-use. The candidate uses only prior exact-key observations and resident state; never future request labels, completions, measured cost of a future request, or protected data. Record the complete source SHA, exact checkpoint/tokenizer hashes, frozen model generation arguments, Python and dependency versions, environment, traffic manifest bytes/SHA-256, and exact controls. Retain 4 cache entries and an 86,114,304-byte maximum resident KV. Cloned request-local KV must never alias resident immutable KV.

Follow G97's original-model adapter only after adding a separately tested, isolated G100 arm; do not overwrite or monkeypatch frozen controls without restoration on all failure paths. Do not dispatch an existing G97 workflow unchanged as evidence for G100.

## Cohorts and measurement

Freeze a new G100 **development-only** traffic manifest, request identities, order, deterministic seed and SHA-256 before first original-model measurement. Preserve the four named strata (round_robin, bursty, mixed, overflow), 48 requests per repetition, four paired repetitions per stratum, identical generation/token counts and pinned GPT-2 CPU settings (2 intra-op / 1 inter-op threads, 3-core affinity). G96 development ranks 276–287 may be used only for development; ranks 288–299 are protected and must not be accessed. Report pairing and cohort reuse limitations explicitly. Use cold checkpoint/cold cache restoration for each paired comparison in the same specified order or freeze an independently seeded balanced order in advance; no post-hoc order selection.

Per arm/stratum report exact token parity; number of requests, hits, misses, admissions, evictions, bypasses, builds, clone/prefill calls; wall time, median throughput, worst paired speedup, p95 latency ratio, total CPU ratio, sampled peak RSS ratio, retained bytes and online decision overhead. Invalid/missing measurements are FAIL, not omitted. Do not confuse counters with measurements.

## Frozen development decision

Every G100 stratum must satisfy exact token parity, bounded residency, median throughput >=1.15x the no-cache control, minimum paired-request speedup >=0.90x, p95 latency ratio <=1.10, total CPU ratio <=1.10, and maximum sampled RSS ratio <=1.15. G100 must also improve overflow wall time over frozen G97 without changing the other arms. Any failed stratum or invariant is DEVELOPMENT_NO_GO. No average improvement can override a worst-case regression.

## Gate sequence and authority

1. Frozen-manifest construction; isolated G100 original-model adapter and adversarial tests including state restoration, original tokens, cache-event parity, full budget and overflow hysteresis.
2. Exact-head Linux/Windows focused + mandatory full regression; preserve source identity after test or workflow changes.
3. Only then, separately invoke the existing authorized development execution route with G100-specific verification and immutable raw artifact/receipt custody; differentiate infrastructure failure, engineering failure and scientific NO_GO.
4. Held-out first-use, scientific acceptance, merge, production cache integration, controller/scheduler changes, and paid model/API execution remain out of scope and require separate authority where applicable.
