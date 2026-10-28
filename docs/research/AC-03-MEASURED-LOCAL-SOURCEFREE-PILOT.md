# AC-03 — Measured software-only resource pilot (development evidence, NOT science)

**State:** LOCAL_CPU_AND_PYTHON_MEMORY_MEASURED / 11 REPERTOIRE WORKLOADS / NO SCIENTIFIC CLAIM / NO ORIGINAL FIRST USE  
**Parent:** Stacked on [AC-02 PR #1055](https://github.com/spoonman136668-ai/FORGE/pull/1055), exact parent commit `eab49b96c759905f8a1723f8f7e12dd75b8d2f88`, which itself stacks on open draft [AC-01 PR #1054](https://github.com/spoonman136668-ai/FORGE/pull/1054). Protected main was observed at `d8bccc604f8607bf10f9d8bc6aa568d1f98af559` before the run. Neither predecessor was merged at authoring.

## Primary evidence and limitations

A source-free local Python standard-library microbenchmark was run on the analysis container on 2026-10-28. **This was not the user's Windows workstation, Wingless, Yggdrasil, a real LLM, an original scientific run, or a FORGE controller/runner result.** Source and complete per-trial machine-readable output are packaged in companion artifact `AC03_measured_resource_pilot_20261028.zip`.

- Artifact ZIP SHA-256: `d0d0968092d220d63af506016134c50f45277ce2ad882ae3b52c8e49c7866131`
- Executed benchmark source `ac03_benchmark.py` SHA-256: `b4295236b37b6b017841a863ab8fd551fee26cdafa8f5b02a4d80afdc78f2c5d`
- 3-repetition raw measurements `ac03_results.json` SHA-256: `53d2bfbe4b1563e10066b7c80893d7271b5f28a8a0a5f69365f68eeb40517126`
- One-run isolated-process spot-check `ac03_isolated_check.json` SHA-256: `d3bbc355e53703aaf7c7330e6621a3896feb8c5a4b1af9205c71a81456bed310`
- The ZIP and source/measurements were **not uploaded into this Git commit**. These exact hashes are archival references only, not GitHub-attested artifacts or qualified provenance. The actual files must be source-pinned and independently qualified before any scientific use.
- Local benchmark tests: 5/5 pass against the local executable. AC-02 bundled predecessor tests: 12/12 pass against the attached development bundle; **not exact GitHub PR CI**.

## Main measured CPU observations

**Metric:** candidate median process CPU time divided by baseline median process CPU time (3 local sequential repetitions of each variant), lower is faster **on this toy Python workload**. Tracemalloc was independently restarted per variant; whole-process high-water RSS in the main run is *not valid* for variant comparisons, therefore recorded NULL. Subprocess launch was excluded from timings. Results are indicative, not statistically powered.

| Workload | Original proposal IDs | Candidate / matched test baseline | Median candidate/baseline CPU | Correctness and caveat |
| --- | --- | --- | ---: | --- |
| Known-neighbor delta update | AC-D1 | Incremental cached terms / recompute entire known expression | **0.048×** | Exact output parity; graph dependencies are hand coded, not learned; global events not covered |
| Precomputed decision upper bounds | AC-D2 | Stop when certified / evaluate all candidate actions | **0.014×** | Exact decision parity; optimistic bound and favorable action order built into generator |
| Memory grouping | AC-D3 | Group equal outcomes / retain every observation in sequence | **1.002×** | Exact query parity; all raw outcomes still retained, so **no memory-saving demonstration** |
| Fitted rule as executable code | AC-D4 | Python compile fitted 3x+5 / direct fitted Python evaluation | **0.658×** | Exact parity; known small synthetic linear rule; no actual program discovery |
| Sparse eligibility updates | AC-D5 | Update nonzero traces / scan full vector | **0.003×** | Exact weight parity; traces supplied a priori, no causal credit learned |
| Degree/role-pruned matching | AC-D6 | Signature-pruned graph isomorphism / brute-force permutations | **0.085×** | Exact parity; graph rename matching **not unfamiliar structural transfer** |
| Zlib decompression, repeated bytes | U01, U09, U14, U17 | Compress once then repeatedly decode / direct bytes | **106.736×** | Exact CRC parity; decompression much slower; not tensor kernels |
| Zlib decompression, random bytes | U01, U09, U14, U17 | Same / direct bytes | **11.203×** | Exact CRC parity; noise not algorithmically compressible |
| Ternary arithmetic | U11 | Python addition/subtraction loop / Python integer multiply | **2.153×** | Exact dot-product parity; **no vectorized CPU kernel** |
| Count-min sketch | U10, U13, U18 | Fixed 4×512 sketch / exact counter | **6.259×** | Approximate only; 1,594 of 1,600 counts overestimated, sum overcount 8,638 |
| File streaming | U12 | 64 KiB chunk read / whole-file read | **1.039×** | Exact CRC parity; OS cache, temporary file and allocation confound |

The isolated-process single-trial spot-check preserved direction for AC-D1 (0.0587×), AC-D2 (0.0205×), AC-D5 (0.0026×), U01-repeated (61.92×), U11 (1.297×), and U13 counting sketch (7.69×). This is **one** separate cold Python process per variant, not a statistical confirmation or Windows resource result. Cold process RSS values include the interpreter and cannot support a model-memory improvement claim.

## Coverage of all user-requested hypotheses

The **complete portfolio remains 30 original document proposals plus six new AC-D1...D6**. AC-02 covers all 36 with inexpensive software toys, restricted information-theory counterexamples and physical-hardware limitations. AC-03's 11 resource workloads sample only selected implementable *restricted variants*. The rest have **not** been measured for capability or performance; absence from this table is not scientific rejection.

Next measured work should target, in independently bounded classes:
1. Retrieval-interference scaling (HDC/holographic/LSH and sketches), actual decision accuracy per byte rather than perfect reconstructability assumptions.
2. Nonparametric speculation with target verification, and time/verification accounting; out-of-core random-access workload with cold storage controls.
3. Reservoir, finite-state/Tsetlin and cellular-automata local *learning* tasks, not demonstrations of recurrence or algebra.
4. Low-rank tensor and graph-rewrite loss/accuracy/cost tradeoffs; executable program synthesis with full search amortization.
5. Semantic fidelity stress tests of spectral, topological, finite-field, hyperbolic, quantum-stabilizer and chaos-based proposals. The software-only versions may be tested as bounded representations, never as arbitrary infinite-capacity memories or hardware quantum/analog speedups.
6. A **genuinely learned** dependency/decision/credit mechanism, then unfamiliar-family transfer with proper fully fitted symbolic/recurrent controls; current source-visible speedups are **not** learning evidence.

## Measurement methodology and control integrity

For each future class, keep exact immutable source/config/harness keys, identical generated observations and task order, paired output checks, strong fully fitted controls and explicit measurement of precomputation, compilation, search, restart, allocations, peak RSS, wall+CPU time and memory footprint. Do not compare Python loops with compiled native tensor kernels as though they were equivalent implementations. Separate warm and cold process measurements; run Windows commodity CPU trials and Linux cross-checks on source-pinned candidates after exact build verification. Negative controls must include worst-case fully connected delta dependencies, misleading decision bounds, interference-driven memory splits, noncausal eligibility traces and structural near-misses.

**Known quality gap:** The local main pilot uses only three sequential repetitions on one host; allocator, interpreter, CPU contention and tracing overhead are uncalibrated. It establishes feasibility/rough direction, not statistically qualified improvements. No hardware bandwidth, energy, GPU/VRAM, native model, unfamiliar transfer, or learned cognitive capability was measured.

## FORGE / ITD-02 authority

This report does not enter an operational queue or claim the controller has consumed it. Existing [ITD-02 #857](https://github.com/spoonman136668-ai/FORGE/issues/857) and [FORGE ADR-0002](https://github.com/spoonman136668-ai/FORGE/blob/main/docs/ADR-0002-MIND-PALACE-ONLY-NO-CKB-DEPENDENCY.md) prevail; independent consequence source for W1 remains `NOT_VERIFIED` at this review. No F139 assignment/eligible labels or new scheduler/controller. Existing NCI-04, ITD-01, Q21, BIO, Mass Research and language/learning work continues unchanged.

`AC03_LOCAL_PILOT=COMPLETE`  
`AC03_EXACT_GITHUB_SOURCE_TEST=NOT_VERIFIED`  
`AC03_NATIVE_WINDOWS_QUALIFICATION=NOT_RUN`  
`ORIGINAL_SCIENTIFIC_FIRSTUSE=FALSE`  
`W1_CONSEQUENCE_SOURCE=NOT_VERIFIED`  
`MODEL_OR_ACCEPTED_REF_MUTATED=FALSE`  
`MERGED=FALSE`

**Next engineering gate:** Commit the actual benchmark source and results under exact source identity, run qualified Windows/Linux trials using existing permitted resources, and then run restricted substantive-learning pilots for the other idea families. Only afterward seek separate FORGE-native scientific admission. Compositional test-result reuse is permitted with exact semantic/harness identity, but one full integration regression remains mandatory before any authorized promotion.
