# Efficient language: source-only development-screen preparation (ELANG-A1)

**Scope:** Additive engineering capability for [FORGE #798](https://github.com/spoonman136668-ai/FORGE/issues/798). Does not supersede active NCI-04, ITD-01, BIO, Mass Research, Optimizer, F139, Q21 or scientific custody. This directory contains **no experiment runner**, source parser for worker dispatch, admission authority, storage cache or automated scheduler.

## Use existing qualified primitives

- `research/q21_information_budget/resource_meter.py` measures process CPU, peak RSS, native I/O and serialized receipt storage. RSS is a **whole-process cumulative high-water mark**, not per-mechanism isolated peak memory; no measured energy unless separately instrumented. Process-local counters cannot be equated with total hardware/infrastructure energy or full experiment cost.
- `research/q21n01_forge_native/matched_controls.py` pins source blobs, conventional trained comparator budgets and exact pre-DEV selection within the Q21N investigation. They are **task-specific**; they are not automatically valid comparators for text generation. For language screens, Research Charter/Optimizer must supply trained language-capable conventional comparators and explicitly freeze training data and budgets.
- `research/r10-mechanism-screen/protocol.py` enforces preregistration, negative evidence and cohort disjointness for its own frozen investigation. Its original/sealed identifiers **may not** be reused as new language-screen cohorts.

## This module's contract

`screen_contract.py` provides deterministic `candidate_key(contract)`, strict `parse(raw)`, `inspect_focused_receipt(contract, receipt)` and `measurement_coverage(metrics)`. An identity binds both candidate **and** conventional comparator Git commit/tree/config, train/dev/holdout content hashes, protocol, environment, meter, focused-test suite and hard development budgets.

The receipt inspector checks only **internal identity consistency**; it unconditionally reports `provider_custody_independently_verified: false` and `cached_qualification_authorized: false`. Source-only matching **cannot** authenticate an external provider, reuse a qualification, skip full integration tests, or claim a measured performance gain. Any later cache reuse requires a separately qualified existing custody verifier with immutable original provider and artifact identities, safe workspace and exact matching source/evaluation context. Unknown measurement values are `null`, never fabricated zeros.

Measurement fields include language fidelity, task quality, training/inference operations, sequential latency, peak memory, storage and energy where observed. Coverage is **not** a proof of scientific efficacy. Reproducible matched-resource study results are separately required before advancing a mechanism.

## Frozen operational limits

- All example/rehearsal objects are development-only and self-denying: no experimental execution, first-use, source grants, accepted-ref mutations, paid API, new controller, scheduler or queue.
- Existing `.github/workflows/qualify.yml` runs these source-only guards on **both** original Ubuntu/Windows qualification jobs; it is not an experiment or workflow orchestration change. Maintain the original one full test/race/vet/build integration regression.
- FORGE `AGENTS.md` and ADR-0002 forbid a CKB-plane runtime dependency; existing higher-level orchestration governance is not permission to connect to private CKB accounts, workflows, ledgers or tokens.
- Evidence of improvement requires a pre-specified baseline of existing end-to-end qualified turnaround, followed by independently attested wall-time reductions under unchanged information, scientific negatives, quality and resource budgets. This code does **not** establish such improvement.

**Next scientific admission** remains separate and blocked until the independent authorized first-use authority, candidate source custody, external comparator training, heldout role provenance, one-shot original leases and FSA eligibility are actually evidenced.
