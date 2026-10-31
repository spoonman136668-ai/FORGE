# ACC-119 — U24 DEV comparison: independent reproduction, **negative preliminary evidence**

**Classification:** `NO_GO_DEV_REPRODUCTION_ONLY`; **NOT** a source-qualified FORGE original execution receipt, full scientific result, code failure, or acceptance authorization.

## Frozen inputs and chain
- Original exact-head comparator code: FORGE PR #1327, commit `a03e58ab1350d2d69fb6cab42b7df921df19bcbf`.
- Frozen design remains `docs/research/ACC-94-U24-CHANGING-RULE-PREREG-20261030.md` and `docs/research/ACC-101-U24-INTERACTING-LOCAL-CELLS-PREREG-20261030.md`; **neither adjusted** in response to outcomes.
- Comparison implementation blob `research/acc95_u24/compare_fitdev.py`: `3d8ecb78efcc8b41c490d37a16bd1496390e5e2f`.
- Exact-head automated Linux/Windows cross-platform #2688 (`41158021630`) and native Windows #567 (`41158021647`) were **PENDING, NO JOBS RETURNED** at inspection. Rehearsal #549 (`41158021582`) completed success; it does **not** prove the ACC-118 comparison ran.
- This independent Python **reimplementation** locally reconstructed the source-free trace generator, update rules, and evaluator for **four DEV cases only** (rules 54/150, seeds 701/709; width 127, 320 steps, 31 visible cells and 96 evaluation cells per step). It did NOT execute the original checked-out GitHub files, the 32 FIT cases, a sealed cohort, or the original CI environment.
- Reproduction script SHA-256 `11be72af20d3b6f47aded9280e68441720bf93657329f9297d3b516aa634f4d6`; local JSON output SHA-256 `6e6cb9bc5d871a737ba81bbfda30f49b9e6b4acbdd59e0609be5b2e94c8c6235`. These local SHA values are *descriptive, not independent source authentication*; the local code and output have not been checked into this branch.

## Preliminary results (four DEV cases only)
Post-switch accuracy and cumulative 64-step adaptation errors:

| Method | Mean post-switch accuracy | Sum adaptation errors |
|---|---:|---:|
| Count-carry (no reset) | 0.8767903646 | 5803 |
| EWMA 0.02 | 1.0000 | 932 |
| EWMA 0.1 | 1.0000 | 217 |
| EWMA 0.3 | 1.0000 | 135 |
| **EWMA 0.7, strongest adaptation baseline** | **1.0000** | **102** |
| Connected local messages | 1.0000 | 135 |
| Messages disabled | 1.0000 | 135 |
| Messages shuffled | 1.0000 | 135 |

Connected versus conservative best baseline: **accuracy delta 0.0**, **adaptation-error reduction -32.3529411765%** (connected 135 vs EWMA 0.7 102); connected vs disabled and shuffled: **no difference in these aggregate error/accuracy metrics**.

| DEV first rule | Seed | Trace SHA-256 | EWMA 0.7 adaptation errors | Connected | Disabled | Shuffled |
|---|---:|---|---:|---:|---:|---:|
| 54 | 701 | `876ddfcb49c0cf6f7fd12597cd90cb5ec5b2fa4ede7617794595a44cb55978eb` | 25 | 39 | 39 | 39 |
| 54 | 709 | `90fee6e4b4064ce31cd6497c7cd060a09a04f3a5c1f4d53623ecd888b3747fb2` | 23 | 23 | 23 | 23 |
| 150 | 701 | `4b1cb334d7e4a97159f4c318559413788613c09fd7ba4ca5d98eccb363f3ce25` | 27 | 30 | 30 | 30 |
| 150 | 709 | `de665133167a5d68b11120999a7fdf5541c4a5816528e7b1c006ba71203698f5` | 27 | 43 | 43 | 43 |

All reported arm/case post-switch accuracies for these four DEV cases were 1.0. This indicates **DEV metric saturation**, not successful unfamiliar-source scientific transfer.

## Fail-closed interpretation
- This reproduction **fails the frozen 5-point accuracy-improvement criterion** and **fails the frozen 10% adaptation-error reduction criterion**. It gives no reason to consume reserved TEST or claim the connected mechanism beats a conventional alternative.
- Even if exact-head original results match, the required fitted recurrent control, raw per-prediction custody, independent cold-process restore, complete RSS/CPU/energy/communication-routing accounting, and scientific witness are **UNVERIFIED**. No model admission or native Wingless/Yggdrasil change.
- An independent reproduction is NOT a source-qualified GitHub workflow run. Compare the four trace SHA-256s, per-case outputs, and deterministic classifications against the exact-original `ACC118_RESULT=` lines in Linux/Windows CI before escalating the verdict. Do not silently substitute this result.
- Do not tune the existing method or preregistration on the DEV outcomes; any genuinely revised candidate requires a separate prior-frozen hypothesis and independent scientific authority.
- No protected TEST rules or seeds were accessed for this reproduction. No runner, queue, controller, production, protected main, or model state changed.

**Decision:** Retain as scoped negative advisory evidence; **NO SCIENTIFIC ACCEPTANCE**.
