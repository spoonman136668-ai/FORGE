# CPU G101 — Causal prefix-KV capture from ordinary prefill (P0)

**Stage:** MODEL-FREE MECHANISM DEVELOPMENT ONLY. Not original-model parity,
performance evidence, frozen development trial, protected first-use, acceptance,
or production code. This is a new mechanism, not an amendment to the G100
DEVELOPMENT_NO_GO verdict.

## Motivation and hypothesis

G100 original GPT-2 development experiment [#41718728653](https://github.com/spoonman136668-ai/FORGE/actions/runs/41718728653)
and its [frozen negative receipt](CPU-G100-ORIGINAL-GPT2-DEVELOPMENT-NO-GO-20261103.md)
showed throughput gains but worst-request failures. New cache admission on
a miss required an additional prefix model forward. Hypothesis for G101:
during an ordinary *full-prompt* causal prefill, the first N key/value
positions already represent the exact-prefix state, independent of suffix
tokens. Compactly clone those positions for a future exact-prefix hit,
rather than executing a second prefix forward.

## Isolated P0 proof contract

- Use only GPT-2-style causal KV tuples of four-dimensional tensors with
  sequence axis -2. Reject invalid layer shape, inconsistent lengths,
  nonpositive prefix lengths, expected-size drift, byte-cap overflow and
  source/clone aliases. Reject before allocating when the budget is invalid.
- Clone the prefix slice into independent compact owned storage. A mere view
  retaining full-prompt storage is forbidden. Reserve at most 86,114,304
  logical resident prefix-KV bytes (same budget as G96–G100).
- The miss uses **one** ordinary full-prompt model prefill; return the same
  full-prompt output for request continuation. The captured prefix becomes
  eligible only for later exact-key reuse. No hidden separate prefix forward,
  lookahead, future outcomes, labels, or timing data are used.
- Test compact slicing, isolation from mutations, false clones, budget drift,
  malformed layouts, suffix independence and a causal toy one-forward oracle.
  Toy parity and optional local PyTorch tensor checks do **not** establish
  original pretrained GPT-2 token equivalence.
- This primitive does not choose a cache admission policy, run decoding or
  publish a speed measurement. Account for prefill, slicing, copying,
  verification, residency, and transient peak RSS in any future integration.

## Later gates (not yet authorized or executed by P0)

P1: Qualify P0 with exact-head Windows/Linux focused and mandatory final
regression. P2: Integrate an isolated candidate into the existing pinned
original GPT-2 adapter. On actual GPT-2, compare prefix slices against
separate prefix-prefill K/V and enforce bit-exact generated-token parity
across misses, hits, suffixes and cache evictions. Verify snapshot
immutability, no aliases and all-in per-request CPU, wall, RSS and byte
accounting, including first-use copy overhead and transient memory.
P3: Before any original-model timed development run, independently freeze a
new development-only traffic assignment, full control list, balanced order,
source identity and admission/NO_GO thresholds. Retain no-cache, LRU, G97
and G100 negative controls as appropriate; never reuse protected ranks
288–299. Require throughput >=1.15x, minimum paired-request speedup >=0.90x,
p95 latency ratio <=1.10, CPU ratio <=1.10, sampled RSS ratio <=1.15,
and resident KV <=86,114,304 bytes; any failed stratum means NO_GO.
A separate original-model performance experiment, scientific qualification,
held-out first-use and production promotion are **not** included in P0.

Authority: existing FORGE research branch and runners only; no new controller,
scheduler, paid inference, PR duplication, main merge or release.
