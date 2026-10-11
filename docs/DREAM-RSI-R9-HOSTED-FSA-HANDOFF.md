# FORGE Dream-RSI R9 — hosted scientific work-order grant boundary

R8 demonstrated actual GitHub-hosted compute on Linux and Windows, with independent Wingless/Yggdrasil lanes and complete deterministic artifact reconciliation. The default FORGE compute architecture no longer requires dedicated research runners.

R9 advances **the trust boundary between an independently functioning FSA and an ephemeral GitHub-hosted scientific worker**, without inventing the missing external FSA infrastructure or running a real experiment.

## Native contract

`hostedgrant.ReviewGrant` verifies a domain-separated Ed25519 authorization against an **externally pinned, independent FSA grant public key**. That key must differ from the separately pinned external FSA checkpoint key. A canonical grant binds: exact FORGE repository/workflow, GitHub run ID, first run attempt, immutable source Git SHA and tree SHA, Wingless/Yggdrasil lane, generation, scientific experiment and chosen cohort, frozen prereg and source scope, FSA authority epoch and archive, canonical first-use plan and consumed proof digest, authenticated STARTED record and high-water, real compute ceiling and original scientific run ID.

It cross-checks the provided FSA source scope against its SHA-256 and verifies a content-addressed, already-consumed `fsagate.FirstUseProof`. Both the grant and scope/proof must be pinned/issued through the *independently qualified FSA*. A GitHub workflow cannot forge authority merely by generating a signature or a JSON claiming a first-use receipt. The positive source-unit tests use deterministic test-only signers and do not demonstrate an independent FSA.

**A successful cryptographic review is NOT permission to execute science.** It returns `CRYPTOGRAPHIC_REVIEW_ONLY_NO_EXECUTION` with `LiveFSAOperational=false`, `ScienceExecuted=false`, `ProtectedReplayLockAcquired=false`, `AcceptedScience=false`, and `IndependentPhysicalCustodyVerified=false`. The FSA must separately atomically acquire/consume an independently protected dispatch lease at actual execution time. This code exposes neither a lease, dispatch, scientific runner, scheduler, cloud credential nor a key issuer.

The CLI `cmd/forge-hosted-grant` checks three bounded, non-symlink, local files (grant, exact frozen FSA scope, separately witnessed first-use proof), exact external grant SHA/public key, independently pinned FSA checkpoint public key and GitHub context. It writes an exclusive-create review file only after all checks pass; it cannot run a scientific primary. Its absent/untrusted input response fails with exit code 2 and no output.

## Actual hosted CI test

The R9 workflow triggers on the explicitly named proposal branch's first push attempt. Two separate native GitHub-hosted jobs run exact SHA/five-file checks, focused signed-FSA tests, full FORGE Go regression, vet/build; Linux runs race tests. **Four additional actual GitHub-hosted jobs** independently test the missing-FSA condition for Wingless/Linux, Wingless/Windows, Yggdrasil/Linux and Yggdrasil/Windows. Each compiles the real R9 verifier, supplies **no protected keys, no first-use proof, no external authorization** and independently proves it exits 2 without writing any output or running science. One final job only reports that all four negative gates passed.

The public workflow uses `contents:read` only, no OIDC grant, cloud secret, scheduler, workflow dispatch, paid account, actual original or accepted-reference mutation. The next authorized science workflow path named inside the future grant does not exist in R9, and thus cannot be invoked by this proposal.

## Remaining independent activation requirements

An actually operational FSA must independently validate/attest scientific source/eligibility, prereg and first-use; retain the original protected monotonic ledger and signed raw evidence; issue a narrowly scoped, one-shot dispatch grant in a separately protected signer; and verify the grant's consumption atomically before GitHub-hosted scientific work starts. GitHub-hosted runners and GitHub Actions artifact retention are *not* protected FSA storage, signing identity or external rollback resistance.

The independent FSA deployment and custody requirements remain [FORGE issue #20](https://github.com/spoonman136668-ai/FORGE/issues/20). Until independently provisioned and qualified, no source-only R1–R9 component may turn `CRYPTOGRAPHIC_REVIEW_ONLY` into `DISPATCH_AUTHORIZED`. F1/F2 are consumed; no replay. This R9 run has zero original scientific experiments, zero accepted promotion and zero production system interference.

### Future trigger detail

GitHub Actions documentation confirms that workflow operations using the repository's GITHUB_TOKEN generally do not trigger further workflows for push events; `workflow_dispatch` and `repository_dispatch` are exceptions. Future FSA-owned autonomous succession should use a separately authorized dispatch event explicitly bound to the authenticated one-shot grant rather than relying on a synthetic push event that fails to fire. Neither dispatch event is invoked in this proposal.

## Acceptance

Source-qualified on native hosted Linux and Windows; all four actual hosted negative gates fail closed with absent FSA authorization; full regression/vet/build and Linux race; exact immutable source and bounded five-file diff. These results establish *handoff refusal* as an engineering property, not a real successful scientific grant or policy-driven autonomous experiment succession.
