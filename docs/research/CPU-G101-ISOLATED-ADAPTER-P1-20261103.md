# CPU G101 P1 — Isolated original-model adapter and parity boundary

**Stage: ENGINEERING ONLY; NO original GPT-2 run yet.** G100 scientific
verdict remains DEVELOPMENT_NO_GO. This module is the proposed G101
capture-and-reuse mechanism, not accepted inference acceleration.

The adapter `research/cpu_g97/g101_original_adapter.py` uses the same
frozen G95 baseline_request and request_decode functions and the G96 LRU
admission budget. On a cold miss, the standard full-input prefill executes
exactly once and a transparent wrapper captures its causal prefix KV during
the first model call. The normal baseline decoder consumes the original full
prefill output. Only after the request completes is an immutable compact
prefix clone admitted, for *later* requests. Hits deepcopy the stored prefix
KV and use frozen request_decode; alias and snapshot checks are mandatory.

All request work—including prefix extraction, hash validation, residency
bookkeeping and cloning—is charged to the request clock. Sampled CPU RSS is
reported explicitly as sampled, not full transient peak. The adapter has no
data selection, model download, performance verdict, protected cohort, or
production activation. It does not monkeypatch a shared controller/module.

Unit tests use a deterministic fake forward and two distinct keys, covering
cold-miss full-prefill reuse, subsequent hits, exact synthetic outputs,
incorrect sizes and lengths, key collisions, and unchanged frozen controls.

Next gate: qualify the adapter on both Windows and Linux, including full
mandatory regression. After qualification, create a bounded **original
GPT-2 parity-only** execution path: compare captured prefix K/V with
standalone pinned prefix prefill, verify bit-exact generated tokens and
cache-state snapshots across misses and hits, and record CPU/RSS/forward
counts. No scientific timing/throughput verdict or protected cohorts may
be inferred from adapter-unit success. Original-model calls require an
independently admitted source and development-only custody.

No change to G100 frozen original-model outcomes, protected ranks 288–299,
cache cap 86,114,304 bytes, or FORGE production/main is authorized here.
