# ACC-G94: temporal activation-delta projection reuse — frozen CPU screen

**Status:** preregistration only, before implementation or measurement. Isolated GPU ACC unconventional-method portfolio PR #1329. The G79–G90 evidence backfill and separate GPT-2 CPU track remain out of scope.

## Hypothesis

For a time-series of hidden states `x_t`, a dense layer projection obeys the identity
`W x_t = W x_{t-1} + W(x_t - x_{t-1})`. If the exact delta has few nonzero coordinates, an incremental calculation may avoid most of the projection. The issue is whether **realistic dense deltas** destroy any performance benefit after charging for sparse-index detection, indexed memory access, and persistent-output updates.

This study proves or falsifies the CPU-proxy mechanism only; it makes no assertion that autoregressive transformer hidden states are sparse, or that model/GPU throughput improves.

## Frozen independent conditions

- Deterministic float64 NumPy; one BLAS thread; `D_in=256`, `D_out=512`, exact matrix `W` drawn `N(0,1/sqrt(256))` per seed; seeds `[9401,9402,9403]`.
- Regimes: `iid` dense independent `x_t ~ N(0,1)` at each time point, negative control; `exact_sparse` the initial `x_0 ~ N(0,1)` and each subsequent transition changes **8 of 256** randomly chosen coordinates by independent normal increments. The latter is deliberately favorable and must not be represented as observed model behavior.
- Generate 16 transitions per seed/regime and one initial state: **3×2×16=96 transition-level cases**. Both arms process identical prerecorded state sequences; no held-out adaptation or cherry-picking.
- Dense baseline per sequence: `W@x_0` followed by `W@x_t` for all 16 transitions, with full float64 BLAS projection. Candidate per sequence: `W@x_0` once, then `delta=x_t-x_(t-1)`, `idx=flatnonzero(delta!=0)`, `cache=cache+W[:,idx]@delta[idx]`; all index finding, gathering, allocations, and cache updates **charged**. No reuse of baseline outputs or cached precomputed delta masks during timed candidate work.
- Measure both complete 17-state sequences via **9 alternating paired trials** (1 untimed warmup for each arm) and median wall-clock latency per seed/regime. The score is `dense_median / candidate_median` and excludes only identical data-generation work. Independently check all 96 candidate state projections against exact dense: `relative_L2<=1e-9`, and report support size, error, finite-state flags for each.
- **NO-GO** if any nonfinite value/error, any transition error above `1e-9`, a missing case, or if median sequence speedup across the three seeds is below **1.15× in either** IID or exact-sparse regime. Otherwise **CONDITIONAL_FEASIBILITY_ONLY**. Asymmetric favorable-only wins fail. The 1.15 cutoff is an exploratory gate, not modification of an existing scientific acceptance threshold.
- Source and all observations must be retained in same draft PR with exact immutable source/CI provenance, never local-only evidence. The CI workflow's regression test PASS is not a performance PASS; classification must read numeric JSON from full runs. Authentic TinyLlama CPU/GPU traces, fully optimized kernels and fresh scientific qualification would be required to advance a survivor.

This frozen screen cannot be retuned after seeing data; any altered threshold, dataset, or control requires a new version. No runner/controller dispatch, paid API, production changes, accepted-ref mutation, merge or promotion authorized.
