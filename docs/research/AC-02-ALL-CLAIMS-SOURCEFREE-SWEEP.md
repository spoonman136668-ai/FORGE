# AC-02 — broad software-only feasibility and impossibility screening

**Disposition:** development-only probes; **not** scientific first-use, admission, a new controller, a FORGE worker task, proof of superiority, or model promotion. No change to running NCI-04 / ITD-01 / Q21 / BIO / L9 programs.

## Dependencies and immutable context

- Stacked on **AC-01 advisory PR #1054** candidate source commit `0e2122701b0f37f061802ae0ef03135420afb30a`. AC-01 is an **open draft**, not an accepted research direction.
- FORGE protected main source at preparation: `d8bccc604f8607bf10f9d8bc6aa568d1f98af559`. Follow [ITD-02 #857](https://github.com/spoonman136668-ai/FORGE/issues/857) and [FORGE ADR-0002](https://github.com/spoonman136668-ai/FORGE/blob/main/docs/ADR-0002-MIND-PALACE-ONLY-NO-CKB-DEPENDENCY.md). FORGE-native isolation and first-use requirements prevail.
- User-supplied document source SHA-256: `4e37ed7736ccc38a3040fc7cf6d0524ce7a4ea4f53bb41491c83c7151f0b6e36`, original headings retained by ordinal U01–U30 in `legacy30.py`.
- Additional original ideas AC-D1–AC-D6 from AC-01 have distinct counterexamples in `native6.py`.

## Scope of the first broad source-free tests

All **30 numbered proposals** from six rounds of the uploaded document are preserved; repeated HDC, program-search and procedural-generation claims retain separate ordinal coverage for provenance. Every record is labeled one of:

- **SOFTWARE_TOY (17):** a tiny deterministic software analogue, arithmetic identity or negative demonstration can execute; this does not imply the proposal's intelligence or performance claims.
- **INFORMATION_LIMIT (11):** a direct counterexample, restricted model class, expressivity bound or finite-memory contradiction invalidates an overstrong form of the claim; useful restricted versions remain researchable.
- **HARDWARE_DEPENDENCY (2):** the claimed physical effect cannot be produced using the described commodity software interface (NUMA-as-HBM, analog resistive DRAM). Pure software simulations remain legitimate but cannot demonstrate physical speedup.

Key limitations to preserve:

| Document IDs | Boundary / next relevant engineering test |
| --- | --- |
| U01, U11, U15 | Real tensor/model accuracy, decode and memory-bandwidth benchmarking, not arithmetic parity |
| U02, U05 | Target-verified speculation and exact cache identity; no near-prompt equivalence assumed |
| U03, U06 | Hardware properties unavailable in pure software; no HBM/analog claim |
| U04, U12 | Real communication, storage latency, OS/cache accounting; synthetic sums/file reads cannot prove practical gains |
| U07, U10, U13, U18 | Retrieval interference, collision rates, usable memory after cold restart and multi-relation composition |
| U08, U19, U24, U27 | Genuine learning and transfer (not a fixed reservoir, toy Boolean table, automaton evolution or manually installed rule) |
| U09, U14, U16, U17, U21, U26 | Minimum-description-length and finite-capacity information lower bounds, plus measured real-world compression |
| U20, U25 | Enumerative search scaling and amortization vs fitted symbolic controls |
| U22 | Error-versus-rank/bond-compression and total compute tradeoff |
| U23, U29 | Phase, causal order, structural/semantic information loss; transforms/topology are not complete language semantics |
| U28 | Modular multiplication and finite-field convolution operation counts; distinguish arithmetic from semantic learning |
| U30 | Clifford-only stabilizer restrictions; no universal quantum or LLM capability inferred |

Six original mechanisms AC-D1–AC-D6 remain independently probed: delta update missed interaction; decision bound certificate; reversible fusion requiring retained information; executable-rule conflict abstention; noncausal eligibility credit; structural relabeling vs genuine new topology.

## Run locally without environment mutation

From the FORGE repository root on Windows (PowerShell) or Linux:

```sh
python -m unittest discover -s research/ac02_sourcefree -p "test_*.py" -v
python research/ac02_sourcefree/native6.py
python research/ac02_sourcefree/legacy30.py
```

Requires Python 3.10+ standard library only; temporary disk data only under OS-managed temp directory. No external requests, training data, API keys, runners, environment access or protected holdouts.

**Verification status:** A local development variant of all 36 probes and **12 anti-overclaim tests** passed on the analysis workstation on 2026-10-28. The exact GitHub commit versions must still be run/qualified by the normal CI or authorized Windows/Linux qualification path; do not transfer local test status as identity-proven CI evidence.

## Follow-up screens (not automatic admission)

Use a two-dimensional disposition for every proposal: **physical/mathematical feasibility** and **measured learning advantage**. No category is erased merely because a broad claim fails; test strongest plausible *restricted* variant where possible. Examples: finite hyperbolic hierarchical indices rather than infinite storage; graph topology as a feature rather than semantic oracle; HDC with quantified interference; low-rank compression with error bounds; stabilizer subroutines rather than general intelligence; out-of-core streaming with actual I/O accounting. If an idea is impossible as specified, its scoped conditional variant is a *new falsifiable hypothesis*, not evidence the original claim was true.

**AC-02 findings are engineering diagnostics only.** Source-independent experiments still require a project-owned independently measured consequence source; currently `ITD-02-W1_CONSEQUENCE_SOURCE=NOT_VERIFIED`. Before a protected original, FORGE must freeze exact source/seed/thresholds, properly trained controls and first-use provenance. Existing F95/F96 and Q21 mechanisms may be reused by exact identity with affected-interface and one required final full regression.

## Non-effects

`PROPOSALS_COVERED=30_PLUS_6`  
`EXACT_GITHUB_SOURCE_CI=NOT_YET_VERIFIED`  
`SCIENTIFIC_ADMISSION=FALSE`  
`PROTECTED_FIRST_USE=FALSE`  
`F139_QUEUE_OR_POLICY_CHANGED=FALSE`  
`MODEL_OR_ACCEPTED_REF_CHANGED=FALSE`  
`NEW_SCHEDULER_OR_CONTROLLER=FALSE`  
`OUTCOME_SOURCE_VERIFIED=FALSE`
