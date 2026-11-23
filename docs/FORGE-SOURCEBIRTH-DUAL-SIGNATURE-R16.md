# FORGE R16 — signed prospective source-birth observation (source-only)

Base: FORGE R15 merged `9f75a03f6519e6f1c967291fef3cf526f65aa27b`.

## New source-level verification boundary

The `sourcebirth` package authenticates a *structural* prospective birth record using two Ed25519 signatures with separately pinned public keys and role-specific signing domains (issuer and independent witness). Both signatures cover the **same immutable statement**: lane, original ID, repository, exact source commit/tree, preregistration/cohort/raw-archive digests, authority epoch, monotonic sequence and witness revision claims, and declared freeze/birth order. The caller supplies independently retained exact expected identities and high-water floors. Wrong source/cohort/epoch, stale floor, same key for both roles, incorrect domain, absent signer or changed signed original fails closed.

A valid result emits a content-addressed read-only observation and explicitly retains all of `physically_independent=false`, `persistent_first_use_proven=false`, `scientific_execution_authorized=false`, and `cutover_authorized=false`.

This is **necessary but insufficient** to prove trustworthy real science. Two public keys and signed chronology are not evidence that independently protected hosts exist, that physical storage is immutable, that wall-clock chronology is trusted, or that a source/cohort was never previously consumed. Authenticated deployment attestation, truly durable external monotonic CAS/high-water, complete all-lane consumed-first-use ledger, signed real-worker start/terminal evidence, retrospective CKB S14 reconciliation and owner revocation remain required. The verifier does not mint signers, run original science, open listeners, use paid APIs or alter any existing controller.

## Qualification

Require independent exact-head Linux full test/race/vet/build and native Windows test/vet/build, negative role/domain/cross-lane/signature/source/epoch/floor tests, and one post-merge full regression. This is a bounded custody-verification interface, not a cutover permit.
