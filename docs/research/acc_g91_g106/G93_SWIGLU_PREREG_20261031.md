# ACC-G93: SwiGLU dead-zone pruning — frozen CPU pre-screen

**State:** preregistered before source/measurements. Independent G91–G106 GPU-track exploratory screen in draft PR #1329; not the separate GPT-2 CPU track, not TinyLlama/GPU evidence or admission.

## Distinct hypothesis from G81

G81 tested synthetic **ReLU** inactive-channel pruning. G93 asks whether the exponentially decaying *negative tail* of **SiLU** creates enough negligible SwiGLU channel contributions to profitably omit rows of the output/down projection while computing gate and up projections exactly. This screen does **not** assume exact zeros or allow omission to be called numerically exact.

## Frozen workloads and controls

- Deterministic float32 NumPy, single BLAS thread; `D_model=128`, `H=1024`, `D_out=128`. For each seed `[9301, 9302, 9303]`: independently generate `W_gate`, `W_up` of shape [128,1024] with `N(0,1/sqrt(128))`, and `W_down` of shape [1024,128] with `N(0,1/sqrt(1024))`; four independent `x ~ N(0,1)` inputs.
- Two regimes, applied to **gate preactivations only**: `iid` with additive bias `0` (negative control); `negative_shifted` with additive bias `-3` (deliberately favorable synthetic case). No actual checkpoint weights, activation distributions or prompt traces.
- Threshold `T ∈ [2, 4, 6]` (exactly these); omit a channel **only** when the gate preactivation `z < -T`. SiLU formula `z/(1+exp(-z))`; multiply by exact up projection. The candidate must recompute both full gate/up matmuls, selection masks, row gathers and the remaining down projection on each invocation; no uncharged candidate precomputation. Baseline is full optimized single-thread float32 NumPy dense gate, up, SiLU and down projection. Weight/bias data reused by both.
- `3 seeds × 2 regimes × 4 inputs × 3 thresholds = 72` frozen cases; all must be reported. Each baseline/candidate pair is warmed once, then timed with **15 alternating paired trials**, including the entire execution path. `relative_L2=||candidate-reference||_2 / max(||reference||_2,1e-12)`; record max-abs error, omitted channels, elapsed medians and candidate vs dense speedup. Numerical stability failures are FAIL.
- A threshold earns **CONDITIONAL_SCREEN_FEASIBILITY** only if all 24 cases (12 per regime) satisfy `relative_L2<=1e-3` and **median** baseline/candidate speedup is `>=1.15×` within **each** regime at that same threshold. Any case error >1e-3 disqualifies that threshold. If no threshold qualifies, `NO_GO_SYNTHETIC_SCREEN`. This **1.15×** is a screening cutoff only, not any scientific acceptance criterion or permission to tune thresholds.
- CPU float32 tolerance/parity is assessed against precisely the same dense computation. Even qualifying hypothetical results would require authentic model traces, optimized fused kernels, real RTX GPU end-to-end performance, held-out workload parity and frozen scientific thresholds before acceptance.
- Pin code and JSON observation provenance to immutable Git commit; no paid API, new controller, accepted-ref or promotion mutation. Console JSON is a measurement artifact only when captured with source and job identity in the existing draft PR. Preserve failures and all 72 cases.

**Status at registration:** no G93 source or measurements executed. Changing parameters after results requires a separately versioned protocol; no retroactive cutoffs.
