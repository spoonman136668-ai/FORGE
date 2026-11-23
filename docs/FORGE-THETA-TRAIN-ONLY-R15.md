# FORGE R15 — frozen training-only adaptive-theta foundation

Base: FORGE `9bdbe08ffa97a26a7c46a40d90025574d22862b6`, following merged R13/R14.

**Status:** source-only candidate-generation infrastructure; NOT a qualified ThetaEvolve research result, scientific-admission authority, autonomous training loop, or production deployment.

## Bounded behavior

`thetaadapt.Adapt` accepts an independently pinned frozen contract and an independently pinned, lane/source-specific training history. The contract freezes source SHA, epoch, feature count (1–16), initial weights, absolute weight ceiling, update step, maximum updates (1–64), total training compute, and the exact training-history digest. Each training observation is ordered, budgeted, unique by evidence identity, explicitly training-only, and records its existing scientific classification. Invalid and consumed/indeterminate records remain in the complete history and cannot alter parameters. Negative and mixed training records are retained as such without reclassification.

The non-executing proposal contains deterministic final weights, full input record count/classification tallies, exact consumed training compute and a content-addressed chain of every bounded update. There are no model calls, original scientific starts, learned novelty claims, sealed holdout access, automatic dispatch, FSA grants, threshold/split changes or hidden parameter growth.

## Required engineering gate

- Exact PR-head native Linux full Go test/race/vet/build and public isolation.
- Exact PR-head native Windows full Go test/vet/build.
- Adversarial validation for wrong lineage, source drift, duplicate/replayed evidence, heldout-like classifications, over-budget updates, invalid/consumed learning, capacity growth and signed-gradient escape.
- Post-merge full regression; default to no authority and no real science.

## Still required for operational ThetaEvolve

Real historical training input must be independently authenticated rather than merely SHA-matched. Reproducible adaptive proposals must outperform fixed-capacity matched controls under preregistered, disjoint, sealed prospective tests before any claim of scientific gain or FSA selection eligibility. This package cannot independently certify a witness, a physical first-use ledger, an external monotonic CAS, or control-plane readiness. It does not supersede existing Wingless/Yggdrasil work.
