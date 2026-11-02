# ACC-G104 — Activation fingerprint with exact collision certification: frozen CPU screen

**Preregistered before any G104 implementation or measurement.** Independent FORGE GPU-bottleneck research slate G91–G106 in draft PR #1329. This is synthetic CPU NumPy, **not** a pretrained model, actual GPU kernel or evidence of accepted throughput improvement. Protected-main baseline `0810ecf3df6378bcbfe5239d30df836b7e12a602`. Research/model, controller and main admission contracts remain unchanged.

## Mechanism and crucial negative control

A coarse quantized activation fingerprint can suggest when an output `W @ x` may be reused. **Fingerprints can collide**, so using fingerprint equality by itself is unsafe. Candidate must compute `blake2b` (digest size 8) on quantized activation coordinates for **each** of the two inputs, and then verify full `np.array_equal(x0,x1)` before reusing a cached output. Otherwise it must recompute the second dense projection. No hash value alone can certify correctness, and no baseline answer/target output may be consulted to decide reuse.

Use `q(x)=rint(2*x).astype(int32)`, then `hashlib.blake2b(q.tobytes(),digest_size=8).digest()`. The first projection, two fingerprints, array comparison, copy-on-hit, and second matvec on miss all count in candidate wall time. Baseline always performs **two** dense `W@x` projections, same arrays. The output is two vectors, not a single shared sum.

## Frozen workload

- float64 NumPy on one BLAS thread; W shape `[512,256]` drawn `N(0,1/sqrt(256))`, seeds `[10401,10402,10403]`. Each seed produces 8 independent base activations in **fixed deterministic generation order**, taking each coordinate from even integer values in [-8,8]. The second input is per-regime:
  - `identical`: a complete *copy* of the base input, so exact reuse is valid.
  - `near_collision`: copy the same base and add precisely `0.001` to coordinate `pair_id % 256`; fingerprints must **still match** in this regime due to wide quantization cells, while the exact full vector comparison must reject reuse (adversarial correctness control).
- Exactly `3 seeds ×2 regimes ×8 input pairs=48` cases, no exclusions. Warm both arms once and time **11 alternating paired trials** per case, comparing both results and all charged runtime costs. Record selected fingerprint collision, exact value equality, reused/not reused, baseline/candidate ms, speedup, finite outputs, max absolute and relative-L2 output errors for the concatenated outputs. No free precomputation or cached fingerprints in timed code.
- Full correctness: `relative_L2 <= 1e-12` on every case, all false-reuse events **zero**, all 24 identical cases reuse, all 24 near-collision cases fingerprint-match but **never** reuse. Any missing case, nonfinite or false reuse is fail.
- Frozen performance gate: **both regimes** must have median measured speedup **>=1.15×** over 24 cases each. If any case fails correctness or either regime fails speed, **`NO_GO_SYNTHETIC_SCREEN`**; otherwise `CONDITIONAL_CPU_FEASIBILITY_ONLY` with NO model/GPU claim.
- Even a hypothetical pass demands authentic transformer activations and true recurrence rates, digest collision model, cache size/memory and eviction costs, optimized fused GPU computation, held-out model quality, end-to-end latency and independent scientific acceptance before integrating into a decoder.

Persist raw all-case data and immutable source/CI SHA in the same draft PR. No paid API, new controller, accepted-ref modification, merge, model first-use, runtime activation or scientific promotion. Any changed threshold or workload after results requires a new preregistered version.
