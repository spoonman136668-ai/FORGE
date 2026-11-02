# ACC GPU-track G91–G106: new unconventional-method screening registry

**Status:** PREREGISTERED HYPOTHESES ONLY. This file is a research proposal, not a result, accepted improvement, or an execution authorization.

**Source baseline:** protected FORGE `main` at `0810ecf3df6378bcbfe5239d30df836b7e12a602`. This branch is isolated from G79–G90 evidence backfill PR #1326 and the separate GPT-2 CPU research track. G76/G77 remain deferred. No CKB-plane controller, model promotion, live runtime, acceptance or paid model APIs are in scope.

## Selection and falsification ledger

| Gate | Mechanism | Mandatory falsifier for initial screen |
|---|---|---|
| G91 | Certified vocabulary elimination via exact group upper bounds | Count exact projected rows including certification work; exact greedy argmax; end-to-end vs optimized dense BLAS |
| G92 | Self-speculated microtrees with shared verification | Net accepted tokens/sec including branch creation and verifier overhead vs standard greedy |
| G93 | SwiGLU dynamic dead channels | Real activation frequency and end-to-end overhead vs optimized dense SwiGLU |
| G94 | Temporal hidden-state delta reuse | Real consecutive-step delta rank/sparsity and full recomputation parity/error |
| G95 | RoPE shifted motif reuse | Prove exact reusable operations under context and causal mask, measure motif recurrence |
| G96 | Block-level attention score elimination with conservative bounds | Bound validity, total QK avoided, score/bound overhead vs optimized attention |
| G97 | Bounded per-head contribution skipping | Prediction overhead and full-layer output error, not standalone head statistics |
| G98 | Geometric low-rank KV representation | Rank/accuracy on held-out prompts with memory and decoding cost included |
| G99 | Outlier-preserving mixed precision | Quantization error plus fused GPU kernel end-to-end vs true optimized baseline |
| G100 | Cold-memory KV prediction and staging | Demand misses, host transfer latency, correctness without uncharged prefetch |
| G101 | Predictive cross-layer residual corrections | Compounding layer error and full decode throughput incl. correction |
| G102 | Confidence-triggered early exit | Accurate early token prediction and verification overhead, unchanged decoding policy |
| G103 | Shape-adaptive kernel dispatch | Full execution time incl. selector and synchronization, no shape-tuned test leakage |
| G104 | Approximate activation-fingerprint reuse | Collision/verification cost and bounded output error against exact cache miss |
| G105 | Token-conditioned precision routing | Entropy/error relationship, switching cost, worst-case output quality |
| G106 | Predictive weight/KV staging | Real timeline overlap and bytes moved, no speculative transfer counted as free |

**Screen policy:** Each screen begins with deterministic no-secret synthetic/control feasibility before authentic model/hardware evaluation. Negative outcomes are retained. Single-kernel speed is not whole-model speed. GPU finalists require unchanged authentic TinyLlama FP16/FP32 comparisons, matched prompts, optimized SDPA and optimized cache baseline, held-out transfer, quality parity, actual RTX hardware measurements and independently frozen admission. No thresholds/splits already frozen for existing projects are replaced by this proposal.

## Frozen G91 screen contract (first inexpensive falsifier)

**Question:** Can a partition-based mathematical upper bound avoid enough output-vocabulary dot products to beat a dense CPU projection *after paying the certification overhead*? This is a CPU NumPy proxy, **not** original GPU evidence.

- CPU data: NumPy float64; one BLAS thread; `D=128`, `V=8192`, `64` contiguous disjoint clusters of `128` rows each. Precisely two regimes: `iid` independent normal rows (negative control); `clustered` each group equals one normal centroid plus Gaussian noise of standard deviation `0.03` (intentionally favorable synthetic control). No training, model weights or real prompts.
- Seeds `[9101, 9102, 9103]`. For each seed/regime, query directions are four independent normal vectors plus four favorable queries aligned with the first four source centroids (only for clustered regime; IID uses eight independent normals). All random draws predeclared and disjoint per seed; favorable queries explicitly labeled—not representative model queries.
- Baseline: optimized `W @ q` dense BLAS and `numpy.argmax`; same dtype and threadpool. Candidate: for each group, compute centroid and maximum Euclidean residual norm at initialization; at query time upper bound `c_g·q + R_g||q||`. Descending bound traversal; fully compute each group's 128 scores until its bound is strictly less than the current exact maximum. Exact ties handled by lowest original global row ID. Certification uses float64 safety slack `1e-10 * (1 + abs(bound))` to avoid declaring false proof near rounding thresholds.
- Deterministic order / recorded outcomes: one global matrix per seed and regime, eight queries, 7 paired alternating measurements per query with warmup, full candidate algorithm and full baseline included; report median milliseconds for each, candidate rows scanned, certified exact-index agreement (0 failures required), and initialization time separately. Include all 6 × 8 = 48 workload cases without post-hoc exclusions.
- **NO-GO** if a single exact winner differs, any nonfinite bound/scores, or aggregate median end-to-end speedup under **1.15×** vs dense BLAS on either IID or clustered regime; favorable-only improvements do not qualify. Any implementation unable to demonstrate rigorous upper bounds is marked invalid. These are exploration triage criteria only, not FORGE scientific acceptance thresholds.
- Environment and artifacts: Python source under `research/acc_g91/`; JSON output to stdout with schema, versions, seeds, controls, raw individual cases and caveats. Source and results must be committed to this research branch to count as durable. Repo CI and CPU proxy do not establish TinyLlama or GPU speedup.

**Research precedence:** Source/prereg commit precedes first measured run. Tests and harness may be implemented after this prereg, but parameters and acceptance conditions above are immutable for G91. Any amended hypothesis requires a new version rather than retroactively moving cutoffs.
