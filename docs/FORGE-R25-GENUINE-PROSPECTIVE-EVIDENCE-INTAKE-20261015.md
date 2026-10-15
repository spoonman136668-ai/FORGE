# FORGE R25 — read-only prospective evidence intake

**Status:** source interface and tests only. No live policy improvement claim.

## Exact scope

R24 [qualified source](https://github.com/spoonman136668-ai/FORGE/pull/262) provides a bounded prospective two-lane Dream-RSI evaluator. R25 connects the existing authorized research owner's future evidence files to that evaluator without creating another FSA, controller, signer, scheduler or first-use ledger.

`cmd/forge-prospective-shadow` has two **required** absolute-path inputs:
- `--owner-evidence`: canonical JSON `forge.dreamrsi.r25-prospective-owner-evidence.v1` with exactly two lanes in Wingless/Yggdrasil order, each with existing immutable optimizer policy, training, validation and future heldout **signed envelopes**, frozen holdout spec and the independently signed per-assignment claim audit.
- `--independent-pins`: separately obtained immutable canonical JSON `forge.dreamrsi.r25-independent-source-pins.v1`. It pins the *raw* owner's entire JSON SHA-256, exact policy-lineage head, train/validation/holdout envelope hashes and signer keys, heldout spec SHA-256, plus separate signed-audit SHA-256 and auditor public key for each lane.

The actual JSON uses the Go struct field names for `dreamrsi.TrustPin` and `dreamrsi.ProspectiveAuditPins`. The CLI validates exact canonical source bytes, ordinary regular files, bounded input sizes and distinct source files, then invokes `dreamrsi.ReviewOwnerEvidence` → the previously qualified R24 `AssessProspectivePair` → the frozen R24 `AssessHoldout` evaluator. No independent pin can be derived from the same untrusted evidence file by the CLI. A pin file's mere existence does **not** prove physical separation or a trusted owner.

### Original owner / signer responsibilities

The current CKB-plane scientific owner (or the *already authorized* FORGE scientific authority after an explicitly accepted cutover) must independently freeze a genuine policy selection **before** prospective outcomes, perform an actual auditable randomized assignment, permanently claim the fresh original first-use before execution, and publish immutable identity-bound STARTED/TERMINAL observations. The isolated auditor must pin keys and exact byte identities in an external trust channel. R25 does **not** launch, generate or sign any of these, and cannot infer a real first-use from signed evaluation data.

Exactly two valid signers' source families remain lane-separated; a missing lane, reused cohorts, observation-after-outcome policy mutation, false signer, missing signed assignment record, tampered original or late holdout fails atomically.

### Observed public research status (2026-10-15)

Read-only API inspection found contemporary Wingless research continuation runs (e.g. `38734125653`) and a Yggdrasil train-only calibration feasibility run (`38729162856`). These checked public run metadata do **not** constitute the separately signed randomized Dream-RSI decision histories with a heldout future cohort that R25 requires. This is not evidence that a signed history does not exist elsewhere; only absence from these checked source surfaces. No positive live owner evidence bundle was provided, so no real prospective gain can be asserted.

### Admission / optimizer restrictions

R25 output remains `SIGNED_PROSPECTIVE_SHADOW_REVIEW_NO_DISPATCH_OR_CAUSAL_AUTHORITY`, and must say `scientific_improvement_established=false`, `independent_first_use_and_source_birth_proven=false`, `scientific_accepted=false` and `optimizer_dispatch_authorized=false`, even if statistical provisional dominance is observed. Real causal gains need a separately qualified, pre-registered prospective test and independent real-randomization audit with multiple-comparison controls.

The other four methods in five-optimizer [draft PR #233](https://github.com/spoonman136668-ai/FORGE/pull/233) remain advisory. This R25 gate does not promote that PR.

**Qualification:** focused tests, one final full Linux and native Windows Go regression, vet/build on exact candidate source SHA. No Cloudflare writes, research interruptions, paid API, Codex review, science dispatch or KTRADE/broker access.
