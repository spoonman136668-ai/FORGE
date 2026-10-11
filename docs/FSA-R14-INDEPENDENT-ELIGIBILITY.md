# FORGE R14 — zero-cost independently authenticated eligibility preflight

**Inactive FORGE source proposal. Not a deployed FSA or authorization for science.**

## Exact prior qualified foundation

R13 draft PR #39 at `32bb40b7d9b432c53912ba642a0b2174235cee04`, Git tree `f808c3220a6bb0671f9cf6fdcda2d835cd72619f`. This R14 delta is additive, not a rewrite of R13 or R1–R12.

## Implemented interface

`fsaeligibility.Issuer` composes with R13's `fsaissuer.Issuer` via the preexisting `fsaissuance.Issuer` interface. Every checkpoint issuance first runs the existing, independently pinned `fsagate.PrepareFirstUse` and `fsagate.ReviewAtAuthenticatedHead` checks using fresh FSA-trusted read-only archive and high-water observations. It recomputes the exact immutable predecision signature, frozen source, preregistration, candidate cohort, compute budget, policy lineage, source qualification witness, proposed STARTED hash, authority epoch and plan SHA. Only an *exactly matching* R13 signed-grant request reaches the signer.

Guard failure, exhausted/started cohort, stale anchor, missing floor, altered prereg/budget/plan, forged predecision or ambiguous archive state **never calls the signer or creates a first-use attempt**. R13's independent signed approval + write-once attempt and the preexisting `CommitFirstUse`'s single external CAS and readback remain required. No automatic retry after an uncertain start.

The Go integration test exercises the real R14 → R13 → R6 library flow across Wingless and Yggdrasil, with synthetic signer and mock CAS floor. Separate negative tests verify that changed eligibility data causes **zero** signer attempts, STARTED appends or CAS. Public GitHub Linux + native Windows qualification runs focused tests then one complete Go regression, vet, build, and Linux race.

## Crucial distinction

The qualified preflight code can make wrong grants fail closed, but **cannot independently authenticate raw source if its claimed FSA data custodian is untrusted**, cannot provide off-host monotonic CAS, protected signing keys, physical loss/replacement resilience, or independent raw retention. Unit tests with temporary keys/files are not real infrastructure qualification. It does not create a FSA controller, scheduler, queue, GitHub research dispatch, or accepted result.

The operator's budget remains **$0 incremental external spend**. Issue #20's physical custody gate and #25's original science, causal histories, and unattended progression remain OPEN. Existing CKB-plane science/KTRADE is isolated and unaffected. FORGE PRs remain DRAFT pending separate independent acceptance and activation.
