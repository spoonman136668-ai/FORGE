# ACC-50 — original U27 typed graph rewriting: prospective native Go benchmark

**Frozen before implementation and measurement.** The original AC-08 name register at `research/ac07_sourcefree/ac08_portfolio.py` Git blob `5126c860771fb024ccfc14c3f7ee8925edf29787` establishes the exact 1-based original **U27: typed graph rewriting**. Research-only baseline commit `45b5d8173538a566bf0f63a8e2ade2dedb6e6166`. This is a constrained typed integer-expression rewrite experiment and cannot establish general model or language acceleration.

Goal: Can a dynamic typed expression-graph algebraic canonicalizer make exact computation faster and smaller overall than independently optimized direct, memoized and compiler-like evaluation, under workloads where algebraic subtrees repeat or don't?

Five source seeds 100101,100103,100107,100109,100111, each 32 independent reset episodes, 2048 public expression evaluations per episode. Four regimes:
- REPEATED: a 32-entry cycle of independently generated depth-4 integer-expression trees.
- COMMUTED: algebraically identical depth-4 binary add/multiply trees with swapped child orders and varying leaf placement (a challenge for structural canonicalization).
- NOVEL: 2048 independently generated depth-4 integer-expression trees per reset.
- CONSTANT: balanced trees whose leaves are constant and whose values can be folded exactly.

Four authentic methods:
1. DIRECT: ordinary recursively evaluated typed int64 trees, checked operations and an exact independent oracle.
2. STRUCT_CACHE: exact conventional syntax-hash interning plus value caching for identical source trees.
3. FOLDED: conventional local constant folding followed by direct typed evaluation.
4. TYPED_REWRITE: genuine type-checked graph canonicalization with deterministic add/multiply commutativity normalization and constant-folding, hash-consing identical canonical subtrees, and exact subtree-result memoization; transformations never change integer meaning.

All operators are integer add and multiply with **defined modulo-2^64 semantics**, no undefined signed overflow. Graph construction/rewrite/caching and independent exact truth evaluation are charged to entire native worker. Each worker emits SHA256 of public source, exact independently computed answers and its predictions, all per-run cache hit counts, compressed logical persistent graph bytes and actual OS peak physical RSS; nothing is inferred from wall-clock as a CPU substitute. All candidate responses must exactly match truth; reject any type or checksum mismatch. The experiment tests typed integer nodes only, not production graph rewrite systems or neural models.

Five paired seeds ×4 cohorts ×4 methods = **80 cold worker processes on each of Windows and Linux**. Whole-child native CPU User+System seconds and wall, OS peak physical RSS (Linux VmHWM, Windows PeakWorkingSetSize), true source parity and 80/80 cross-OS output parity mandatory. The broad all-cohort resource positive requires TYPED_REWRITE complete-worker median CPU <=0.90× fastest conventional, OS peak RSS <=1.10× corresponding conventional, persistent typed graph bytes <=0.75× DIRECT baseline graph bytes and exact output across all four regimes both OS. Missing worker, 0 CPU/RSS, nonfinite, original name mismatch or cross-platform mismatch => `ACC50_U27_BLOCKED`. Valid failures => `U27_NO_GENERAL_VERIFIED_NATIVE_GO_RESOURCE_WIN`; full restricted pass => `U27_RESTRICTED_GO_ENGINEERING_POSITIVE_ONLY` (not native-model acceleration).

Keep 36-registry negatives, focused Go tests/vet/build, reproducible code-hash custody, raw artifacts, and strict cross-platform independent audit. This draft branch does not edit protected main, existing controller/autonomy, Wingless/Yggdrasil native models, CKB-plane, Mind-Palace or paid APIs. No post-result source/threshold changes without new prereg.
