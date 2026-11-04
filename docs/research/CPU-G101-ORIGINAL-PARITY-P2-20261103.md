# CPU G101 P2 — Pinned original GPT-2 correctness-only diagnostic

Status: ADAPTER PARITY HARNESS ADDED; NOT YET EXECUTED ON ORIGINAL GPT-2.

This diagnostic is not a new performance experiment. It reuses only the
already-consumed G100 development ranks 276–285, never the protected cohort
288–299. It loads the exact G95 GPT-2 revision, weights and frozen dataset,
using the same pinned CPU model environment. It verifies the G101 candidate
and an unmodified baseline on a ten-request sequence spanning five exact
prefixes; the four-entry LRU must produce cold misses, hits and evictions.

Checks are fail-closed: model/dataset hashes and runtime identity, KV bit-exact
prefix slices against separate prefix-only prefill for two different suffixes
per key, identical generated tokens for all ten requests, one forward per
generated step (including only one ordinary full prefill per miss), admission
counters and residency cap. All forward probes and oracle prefix-prefills are
separate diagnostic costs and are **not** speed measurements. The receipt
declares `performance_verdict=NOT_EVALUATED`, `heldout_executed=false`
and `promotion_allowed=false`.

A separate guarded workflow execution can be admitted only *after* focused
tests and mandatory exact-HEAD Linux/Windows regression pass. Original-model
parity must pass before building a separately frozen G101 performance
protocol. If literal KV equivalence fails due to CPU shape-dependent
numerics, retain the authentic FAIL receipt and distinguish it from
generated-token parity rather than relaxing the requirement silently.

G100 remains DEVELOPMENT_NO_GO. No production, main-branch, or protected
cohort action is authorized.
