# FORGE FSA R6B-P2: independently witnessed fault-drill evidence contract

Exact source-qualified parent: `9be950113c113695b9cef13adf088b8f21bb1d94` (R6B-P1). This is an **inactive, read-only documentary validation milestone**, not a declaration of successfully provisioned physical infrastructure.

## What the gate actually validates

`fsaprovision.VerifyDrillReport` requires a separately immutable, externally pinned provisioning bundle; an independently supplied nonce/challenge; an exact source commit; the externally pinned SHA-256 of the *complete signed report*; and an independent auditor Ed25519 public key distinct from each role attestor.

The auditor-signed report must describe **all five** fault drills in fixed order: authority host loss, witness host loss, floor host loss, authority/witness network partition, and authority host replacement. Each includes SHA-256 pointers to isolation traces, recovery traces and externally retained observations; an unchanged science head and floor revision during the isolated fault; and signed claims of fail-closed behavior, no CAS replay and no unauthorized advancement. Host replacement must reference a distinct externally provisioned bundle. Duplicate, missing or reordered drills; evidence gaps; forgery; stale challenge; changed source commit; shared attestors; epoch/bundle drift; noncanonical JSON and equivocation are rejected.

**This verifier checks a documentary claim.** A valid signature and digest do not prove the fault actually happened, the evidence was honestly collected, off-host monotonic storage is real, sites are geographically/power-network distinct, or the host replacement retained the protected witness. No production readiness, scientific acceptance, service activation or automatic recovery follows from `VerifiedDrillDocument`.

## Required real-world execution before any physical R6B pass

1. Provision an authority host, witness host and independently controlled rollback-resistant floor with **verified** distinct infrastructure and key custody. Capture immutable, externally audited host, storage, failure-domain and certificate evidence. Do not place all three on the existing Windows research machine, on three runners sharing its host, or in one failure domain.
2. From an independently controlled observer, freeze the signed R6B-P1 provisioning bundle and source SHA and issue a never-reused challenge. Securely witness the current authority head and floor high-water *outside* the affected site.
3. Conduct the five drills **only in an isolated non-production sandbox**. For loss and partition cases, independently record the actual fault mechanism and network/power traces, ensure no work is accepted without the witness, retain the monotonic floor, and compare pre/during/post commitments. For host replacement, provision new protected site identity under a new pinned bundle before reopening any service.
4. Seal the original raw measurement traces and external storage retention witnesses by SHA-256; have a separately pinned independent auditor sign the report after inspecting raw evidence, not merely the site's own declarations.
5. Run this exact verifier against the externally pinned challenge, report digest, independent auditor key and bundle. Then perform a **separate** physical-inspection and scientifically authorized end-to-end admission/continuation gate. Fail closed on any contradiction or missing proof.

**Qualification today:** public Linux full Go tests/race/vet/build/isolation plus native Windows full Go tests/vet/build on exact commit. Adversarial synthetic unit tests qualify only the source contract.

**Explicitly not qualified:** actual physical independence, host deployment, power-loss durability, replacement recovery, partition resilience, hardware custody, scientific source admission or unattended progression. FORGE remains draft/inactive; CKB-plane alone owns current runtime, queue, qualification and acceptance authority. No new scheduler, consumer, runner or competing authority is created.
