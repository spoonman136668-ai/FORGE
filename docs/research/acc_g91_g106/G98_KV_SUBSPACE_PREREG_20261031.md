# ACC-G98 — Geometric KV subspace compression: frozen pre-screen

**Registration occurs before any G98 implementation or measurement.** Existing GPU-bottleneck G91–G106 research draft PR #1329; this source-free synthetic CPU screen is separate from authentic RTX/TinyLlama and separate GPT-2 CPU experiments. FORGE pinned base main `0810ecf3df6378bcbfe5239d30df836b7e12a602`. No scientific acceptance, new controller, paid API, deployment, or model mutation.

## Hypothesis

A query's attention scores may use a compressed key subspace: if `K≈A_k B_k` and `V≈A_v B_v` with data-fitted truncated SVD of rank `r`, compute logits `(A_k @ (B_k @ q))/sqrt(d)` and approximate output `(probability @ A_v) @ B_v`. Query-visible operations are charged, including softmax, rank projections, and all matrix multiplications. Per-KV preprocessing is recorded separately, deliberately not charged to per-query latency (optimistic amortization). This is **approximation**, never a certified exact replacement. Using synthetic *low-rank-generated* tensors as a favorable condition does not demonstrate low-rank structure in an actual model.

## Frozen controls and thresholds

- NumPy float64, 1 BLAS thread, `N=512` KV positions, `D_k=D_v=64`, ranks `r∈{8,16,32}`; seeds `[9801,9802,9803]`, regimes `iid` and `lowrank_favorable`, eight independent unit-scale normal query vectors per seed/regime.
- `iid`: independent `N(0,1)` for every K and V entry. `lowrank_favorable`: form K and V independently from `N(0,1)` factors [512,8]@[8,64] each, scaled by `1/sqrt(8)`, then add independent `N(0,0.001)` noise to each, *not* observed model structure.
- For each seed/regime generate one K,V and queries, compute their independently fitted truncated singular vectors once per candidate rank. A rank's precomputation is excluded from per-query timing but measured and reported. No target-query leakage in SVD: queries sampled after K,V generation, SVD uses only K,V.
- Baseline: exact dense stable softmax over `K@q/sqrt(64)` then `p@V`; candidate `a_k@(b_k@q)` then stable softmax and `(p@a_v)@b_v`. Both float64, no cached baseline logits/probabilities. All candidate per-query work charged.
- Frozen **3 seeds × 2 regimes × 3 ranks × 8 queries = 144 paired cases**. Exactly **7 alternating paired trials** per case after 1 warmup each arm. Report median baseline/candidate milliseconds, speedup, rank, max-abs and relative-L2 output error, measured spectral reconstruction ratios for K/V, and per-KV compression setup time. Do not drop failed queries or choose rank after results.
- Every candidate arm must be finite. A *single rank* qualifies conditionally only if **every one of its 48 cases** (24 each regime) meets `relative_L2<=1e-3`, and median speedup is **>=1.15× in each regime**. No favorable-only promotion; otherwise `NO_GO_SYNTHETIC_SCREEN`. These exploratory controls do not modify accepted project scientific thresholds.
- Even if CPU proxy passes, require original pretrained TinyLlama KV traces, realistic context diversity, model quality parity, memory/RSS accounting, fully optimized CUDA/SDPA and independently qualified GPU first-use before claiming improvement. The screen is a cheap falsifier, not a final admission.
- Evidence: source and full 144-case outputs must be retained in the same PR with immutable source/CI identity; failure is a valuable result. Frozen settings cannot change after measurement without an independently versioned protocol.

**At this preregistration:** zero G98 results, original model untouched.
