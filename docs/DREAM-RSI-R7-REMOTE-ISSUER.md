# FORGE Dream-RSI R7 — mTLS authenticated external FSA issuance client

**Source-only candidate; no deployed issuer, protected FSA key, real FSA service, original science, or autonomous dispatch.**

## Purpose

FORGE R1–R6 already implement signed observation, bounded Dream-RSI policy improvement, independent FSA archive eligibility review, immutable first-use plan, FSA-owned one-shot journal/CAS and read-only indeterminate recovery. Until R7, R6's `fsaissuance.Issuer` interface only had local deterministic test implementations. R7 introduces a **real network-capable client implementation** of that exact FSA-owned interface, without embedding an FSA signing key or offering execution/scheduler APIs.

`fsaremoteissuer.Client` uses a strict HTTPS issuer endpoint with TLS 1.3 minimum, separately supplied trusted roots, client certificate for mTLS, the server certificate's exact SPKI SHA-256 pin and disallowed redirects. Independent FSA archive-authority and witness endpoint URLs are required and must be distinct from the issuer and each other. Hostname inequality is **not evidence of distinct infrastructure**; external physical inventory and faults remain required. The client will not discover trust pins or endpoint identities from GitHub, workers, CKB-plane, KTRADE, the optimizer or the server it is contacting.

## Two independent FSA signatures

The client sends a bounded JSON `forge.fsa.remote-first-use-issuer.v1` POST to `/v1/fsa/issue-first-use` with the R6 `fsaissuance.IssuanceRequest` and a fresh 256-bit cryptographic challenge. The independently controlled issuer must return:

1. An FSA `fsahead.SignedHead` signed by the **separately pinned FSA archive-head key**, referencing exactly the requested old and new archive high-water sequence and SHA.
2. A `forge.fsa.independent-first-use-approval.v1` approval record, signed under a **different independently pinned approval key**, binding request digest, checkpoint digest, exact archive/cohort/lane/epoch, caller challenge and independent approver key ID. Verdict must be `FSA_INDEPENDENT_FIRST_USE_APPROVED`.

The client verifies both signatures and identities before yielding the checkpoint to the existing R6 FSA `CommitFirstUse` function. Wrong server certificate, client identity, redirect, broken authorization signature, wrong checkpoint signer, stale response challenge, different cohort/head/lane or changed request is rejected. Network failures and malformed responses are **uncertain**, never silently retried. The returned certificate does **not** grant science dispatch or replace R6's complete protected archive, first-use CAS and stable independent readback.

A remote HTTPS responder that merely signs bytes requested by the caller is **NOT an independently qualified scientific issuer**. Actual FSA service implementation must independently reread frozen eligibility, issuer authority, original cohort first-use and source witness before signing; it must protect keys and approvals from the optimizer. This module is *only* an authenticated client transport for an independently trusted future service, not the remote server.

## Reproducible qualification

The test suite starts ephemeral, in-process TLS 1.3 services with a temporary test CA, generated server and client certificates and independent throwaway Ed25519 approval/checkpoint keys. These are **not** production credentials, not distinct physical nodes, not an independent FSA, and not accepted results. Tests cover mTLS, pinned key, two signatures, exact request binding and freshness, missing pins, same-key collision, denied/malformed/redirect responses, no automatic retry, foreign-lane rejection and unique challenges. Native Linux and Windows full FORGE Go regressions and Linux race are required.

```sh
go test -count=1 ./fsaremoteissuer
go test -count=1 ./...
go vet ./...
go build ./...
go test -race -count=1 ./fsaremoteissuer
```

Scope: exactly four new files relative to R6 qualified `dbff6e0f192119dede271f6049fd7bd13edbd3ef`. No change to existing FSA archive, optimizer, original scientific work, F1/F2 consumed cohorts, CKB-plane or KTRADE.

## Activation readiness and real physical gate

**NOT READY.** The physical [FORGE #20](https://github.com/spoonman136668-ai/FORGE/issues/20) gate remains blocked: no independently inventoried and approved signer/authority/witness/storage domains, no independent protected key custody, real atomic rollback-resistant CAS, physical power/partition/replacement fault trial or durable external raw evidence. This R7 code adds no cloud VM, paid subscription, permanent TLS identity or signing service. Do not claim the in-process network test satisfies the required off-host 3-domain independence.

**Next actual milestone:** operator-authorized real infrastructure inventory and FSA service deployment with independent key custody, bounded fault-qualified autonomous science pilot and genuine randomized policy logs, train/validation/sealed holdout, independent causal evaluation, two unattended new generations and 24-hour soak. Production dispatch, accepted refs, and scientific acceptance remain solely FSA-controlled and are not activated by R7 qualification.
