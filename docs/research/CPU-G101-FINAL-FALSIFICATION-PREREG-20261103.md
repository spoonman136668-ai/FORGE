# G101 — One final frozen causal-KV falsification experiment

**Protocol status:** FROZEN BEFORE FINAL ORIGINAL-MODEL EVALUATION.
No protected first-use, no acceptance, and no production change.

## Scientific question

In CPU GPT-2 FP32 with the same frozen original weights, can any of the
existing `sdpa` and `eager` causal attention implementations yield
**bit-for-bit identical** reusable prefix key/value tensors when computed
as part of a full-prompt prefill versus when computed by an independent
prefix-only prefill, with **zero additional prefix forward passes** in
the served request path?

An initial G101 original-model parity run at
https://github.com/spoonman136668-ai/FORGE/actions/runs/41733947792
found 0/10 bit-exact prefix/suffix comparisons under the default CPU
backend (although generated tokens matched). Its negative receipt is
`docs/research/CPU-G101-ORIGINAL-GPT2-PARITY-FAIL-20261103.md`.

## Frozen one-shot comparison

- Pin original GPT-2 source weights `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`,
  original dataset `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`,
  original G95 ranker and frozen environment: torch `2.5.1+cpu`,
  transformers `4.48.3`, CPU 2/1 threads and 3-core affinity.
- Only previously consumed development ranks 276–285. Protected ranks
  288–299 are forbidden. Five prefix keys, including one overflow key.
- Both native model attention paths: `sdpa` and `eager`, loaded with
  `attn_implementation` explicitly set, identical weight and tokenizer
  identities and FP32 inference without autocast. No tunable tolerance.
- On *each* backend, for each of five prefixes, compare separate-prefix
  KV tensors with compact slices from full-prefill computations using
  the two preassigned suffixes at development indices `pid` and
  `pid+5`: 10 prefix/suffix cases, 12 layers, 24 key/value tensors
  per case. Record every tensor's bit-mismatch count, total elements,
  maximum absolute difference and maximum integer-ordered ULP distance.
- Also run the ten frozen G101 requests with four-entry LRU, cold-state
  misses, later hits and evictions. Require generated-token equality to
  the original no-prefix-cache baseline, precisely 80 candidate model
  forwards, **no extra prefix-only forward**, immutable/owned compact
  storage and resident KV <=86,114,304 bytes. Diagnostic *oracle*
  prefix runs are explicitly separate; neither diagnostic run is a
  performance benchmark. Record model-call counts and CPU RSS evidence.
- A separate model-free receipt validator recomputes bit-exactness and
  the decision from complete raw per-layer data. Incomplete or corrupt
  outputs are an engineering FAIL, not a scientific result.

## Predetermined decision (cannot be changed after observing result)

If **either** backend passes all 10 cases with zero bit mismatches in all
240 K/V comparisons, and retains exact generated tokens, bounded resident
KV and zero extra served-request prefix forwards:
`EXACT_CAPTURE_FEASIBLE`. This is feasibility only, **not**
performance admission or production acceptance.

Otherwise, if both backends complete all measurements and fail strict
identity: `RETIRE_G101_EXACT_CAPTURE`. Do **not** loosen equality,
add hidden prefix computation, tune this mechanism again, or run a new
G101 timed experiment. Redirect CPU research to a different mechanism.
Engineering failure stays FAIL / UNVERIFIED and does not masquerade as
negative science.

This is the last authorized G101 hypothesis test. Any further G101
research requires a new explicit decision; protected data and production
remain blocked.
