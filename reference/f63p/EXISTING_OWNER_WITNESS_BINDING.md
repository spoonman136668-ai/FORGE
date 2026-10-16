# F63P — existing-owner witness-source binding, no optimizer activation

**Exact parent:** F62P \`211ff47c2eeec87f86109dc82b93cecfd482b15e\` (PR #320).
**Scope:** one bounded source-only read-only witness binding per Wingless and Yggdrasil lane. This branch does not implement a new authority or alter CKB-plane, FORGE workers, Cloudflare D1/Worker, or frozen Dream-RSI/Pareto production selection.

## What changed

- \`ObserveF63PExistingOwner\` requires BOTH separate lane nominations bound to the F58 immutable controls and a lane-specific F61P exact 1/6 prospective assignment plus F62P rational evidence intake.
- Requires the *preexisting* optimizerbridge.Trust verifier to accept actual \`ProspectiveSelection\` source claims. A test-only stub cannot stand in for operational trust.
- For each lane verifies a canonically marshaled predecision witness claim under an independently provisioned Ed25519 public key; binds a separately supplied expected SHA-256 pin, existing owner source identity, assignment digest, public candidate slate/source family/equal-budget commitments, first-use receipt, original outcome receipt, ledger high-water and external ledger head. Keeps identities distinct across lanes. Fails closed on missing/mismatched pins, signature, reuse, or source drift.
- No changes to the frozen Dream-RSI research-action basis-point replay or F62P policy-arm 1/6 ratio, no hidden imputation of absent outcomes. Owner/witness validation is read-only; it never signs, writes, consumes first-use, or submits a job.
- Outputs a source-signature verification report; **every execution/activation/causal/Theta field stays false**, even when a cryptographic fixture passes.

## Required real operational evidence

An externally pinned witness public key and SHA alone establish only consistency of a signed *claim*. They **do not prove** the independent source, signing custody, non-cherry-picked random draw, irreversible ledger registration, remote monotonic high-water, or that the record was durably established *before* an original happened. The owner must provide these separately under its pre-existing authenticated authority and existing Cloudflare first-use controls, with independent outcome review and source-birth eligibility. Once authentic real evidence is available, it must be externally assessed against these bindings; synthetic passing tests are not operational clearance.

This branch builds directly on PRs #317, #319, #320; keep it **DRAFT**. No new controller, scheduler, signer, Cloudflare secrets or writes, paid API, automated Codex review, research interruption, KTRADE operation, experimental original, accepted-reference mutation or policy promotion.

**Status:** F63P source/witness binding engineered. Genuine witnessed prospective first-use is **not** established by this repository or its source tests.
