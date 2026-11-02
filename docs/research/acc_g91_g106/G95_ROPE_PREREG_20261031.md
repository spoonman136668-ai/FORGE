# ACC-G95 — RoPE shift-invariant motif replay: frozen adversarial CPU screen

**Status at preregistration:** NO G95 source, measurements, authentic pretrained-model trace, GPU execution or scientific admission. This is an independent G91–G106 exploratory screen on draft PR #1329, not the separate GPT-2 CPU line. Baseline lineage: FORGE main SHA `0810ecf3df6378bcbfe5239d30df836b7e12a602`. G94 remains separately pending.

## Mechanism and limitation

Rotary positional embedding (RoPE) has a relative-rotation identity: when **unrotated** query and key vectors are unchanged, the dot products for the same token-pair offsets are invariant to a common absolute-position shift, within numerical error. This does **not** imply that identical token text yields identical Q/K in a contextualized transformer. A repeat-motif cache must check actual pre-rotation values (or a rigorously sufficient identity) before replay. No hashing, token-string equality or other potentially colliding fingerprint may act as a correctness certificate.

Falsify replay's value once equality checking, rotation, matrix multiplication, and fallback work are charged. A cache hit must remain exact within a frozen floating-point tolerance, and a miss must recompute. Both exact-match synthetic and intentionally context-shifted negative controls must qualify; favorable-only gains do not pass.

## Fixed workloads, measurement and controls

- One-CPU-thread NumPy float64 proxy; dimensionality `D=64` (32 RoPE pairs), motif length `L=16`. Three seeds `[9501,9502,9503]`; each seed has independent Gaussian `Q, K` matrices [16,64]. RoPE frequency per pair `10000**(-2*i/D)`, with i in [0,31]. Positions for first motif `[0..15]`, second motif `[shift..shift+15]`, shifts `[17,73,511,4097]`.
- Two regimes: `identical_pre_rope` reuses identical Q/K (best-case reuse); `context_drift` draws new independent Q/K [16,64] per shift (negative control), in fixed seeded order. Both regimes use identical baseline/operator math.
- Exactly `3 seeds × 2 regimes × 4 shifts = 24` distinct paired workloads. No outlier removal or tuning after inspecting results.
- Baseline **per paired workload**: rotate original Q/K at positions 0..15; compute original 16×16 score matrix; then rotate second Q/K at shifted positions and compute second 16×16 score matrix. Rotate/matmul cost for both is charged.
- Candidate **per paired workload**: rotate original Q/K and compute first score matrix; test full exact `np.array_equal` of both unrotated Q/K pairs; if and only if both match, return a copy of the original score matrix for the second occurrence; otherwise rotate and compute the second matrix normally. All equality tests, allocations, fallback calculations and copy costs are charged. The first occurrence's result cannot be obtained for free.
- For each workload independently, warm both arms once, then record **15 alternating paired wall-clock trials** and median time per arm. Check finite outputs and `max_abs_error<=1e-9` for both first and second score matrices; store hit/miss flag, normalized error, baseline/candidate milliseconds and speedup.
- **NO-GO** if any case incorrect/nonfinite, any hit in `context_drift`, any miss in `identical_pre_rope`, or if **either** regime has median candidate/baseline speedup < **1.15×** across its 12 cases. Otherwise `CONDITIONAL_FEASIBILITY_ONLY` (not GPU performance). This 1.15× is a G95 exploratory cutoff, not a frozen project scientific criterion change.
- If exact Q/K equality becomes impractical for contextual real-model workloads, the proposal is intrinsically inapplicable absent an alternative collision-free, validated certificate. No source-specific workload cherry-picking. Even a passing CPU proxy requires authentic TinyLlama traces, optimized fused kernels, full decoder throughput, parity and separately authorized scientific qualification.

Persist exact source and all observations in FORGE GitHub draft PR with immutable source/CI identity. No paid API, new controller, runner dispatch, main merge, model promotion, accepted-ref mutation or claim of autonomous execution.

**Preregistration is intentionally upstream of implementation.** Any changed parameters or decision logic require a separately versioned screen.
