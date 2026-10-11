# FORGE Dream-RSI R5 — FSA-owned signed first-use commitment and reconciliation

**Status: source-qualified simulation of existing FSA first-use protocol, NOT activated research dispatch or independently provisioned FSA.**

FORGE Dream-RSI R1–R4 supply authenticated history evaluation, bounded exploration optimization, prospectively signed predecision records, and independent FSA scientific-eligibility *read* checks. R5 adds the exact missing **first-use intent → FSA-issued checkpoint → stable independent readback** contract. It does not create a new scheduler, scientist, trust service or signing key, nor does it append or commit any real original science.

## Transaction boundary

`dreamrsi/fsagate.PrepareFirstUse` calls R4 `ReviewAtAuthenticatedHead` against a genuine FORGE-private `researchlog.Journal`, an independently authenticated FSA `fsatrust.Authority` and a separately pinned FSA scope. It requires a new STARTED receipt SHA and a bounded, immutable original run ID. It then projects a single exact `PRIMARY_STARTED` entry **in memory only** via the existing `researchlog.Append`, preserving the source-prereg-qualified lineage, cohort identity and the precise previous FSA anchor. Output `FirstUsePlan` contains the canonical predicted next sequence and record SHA, is content-addressed, and explicitly says `EXTERNAL_FSA_ISSUER_REVIEW_REQUIRED`. Its commit, scientific acceptance and dispatch flags are all false.

Only a **separately qualified and activated** FORGE FSA may independently sign this projected checkpoint under its protected signing identity, append an original STARTED record to its authorized write-once journal, and atomically compare-and-swap its independently retained, rollback-resistant high-water. The existing `fsatrust.Advance` contract already validates that complete journal, signature, archive and source predecessors before CAS and independently rereads the head. A signed plan is **not** an authorization.

`ProveFSAFirstUse` is read-only. It accepts the independently pinned immutable plan and FSA-signed checkpoint, verifies signed predecessor and exact planned STARTED successor against the FSA's independently pinned public key, then calls `fsatrust.Recover` to confirm a stable external high-water and **complete private archive**. Finally, it compares the latest journal event field-by-field against the exact immutable planned STARTED record. Only this independently observed state yields `FSAFirstUseCommitted=true` and `FirstUseConsumed=true` **in the returned proof**; the proof explicitly retains `PhysicalIndependenceDemonstrated=false`, `DispatchAuthorized=false`, `ScientificAccepted=false`, and `AcceptedRefMutation=false`. An externally committed first use must never be replayed, even when the original science failed or was interrupted.

## Ambiguous and failed commits

When the FSA's protected CAS times out **after** potentially applying, the caller must not repeat it. Test fixtures exercise existing `fsatrust.Advance` returning `ErrCommitIndeterminate` while applying once; the R5 proof reconciles via external FSA **read only** with zero new CAS attempts. If the external service is unavailable, an identity/head changes, the local STARTED exists but protected CAS did not complete, the raw scientific origin is unknown, or a competing writer advanced the head, the result is `ErrFirstUseUncertain`, no dispatch and **no automatic repair/replay**. A denied CAS leaves a locally consumed STARTED event requiring independent recovery; never assume rejection restores eligibility. FSA must have an external failure-safe reconcile/resume policy before unattended science can be activated.

## No time-of-check-to-time-of-use shortcut

The R4 review and the R5 plan are **snapshots**. A concurrent candidate may advance the archive between review, STARTED and external CAS. In that case the R5 planned sequence and successor SHA no longer match the exclusively appended record or the externally signed checkpoint, and `fsatrust.Advance` refuses to acknowledge a different next head. Correct activation requires the FSA writer to serialize *all* eligible events through **one external protected authority and monotonic first-use floor**, with independent witness retention and protected key custody. This source-only proposal does not install that infrastructure or turn a test mock into real independence.

The pending physical [FORGE gate #20](https://github.com/spoonman136668-ai/FORGE/issues/20) explicitly lacks proven independent failure domains, key custody and an externally durable monotonic floor. Unit tests therefore use an in-process fake FSA authority and a local FORGE archive. The test private key **exists only in test code**; the production module has no signer, no static secret, no hostname, no storage enrollment and no network or worker launch.

## Qualification and adversarial tests

- Exact qualified R4 source `6ad6bb626ec99959d7f730d0ff54b9eaa3c97c25`, strictly additive R5 files.
- R4 FSA read review and first-use plan do **not write** the archive or perform CAS.
- Independently formed and signed mock-FSA checkpoint; one local append, exactly one mock-CAS, confirmed protected readback; a second scientific start fails.
- A mock FSA CAS that commits but loses its response: reconcile with read-only proof, **never retry** the CAS or original.
- Denied FSA CAS, unavailable or forked authority, untrusted signing key, changed predecessor, altered pinned run/cohort/witness and second or racing STARTED: blocked.
- Both Wingless and Yggdrasil lane-specific source, prereg, witness, cohort and first-use separation.
- Hosted native Windows + Linux focused tests, one complete FORGE regression, vet, build and Linux race.

```sh
go test -count=1 ./dreamrsi/fsagate
go test -count=1 ./...
go vet ./...
go build ./...
go test -race -count=1 ./dreamrsi/fsagate
```

## Readiness assessment

**R5 deliverable:** a source-qualified, typed, content-addressed, FSA-owned first-use **commitment and reconciliation protocol**, directly integrated with the existing FORGE scientific event journal and the installed FSA trust interface.

**Not delivered or implied:** actual independently hosted/key-controlled FSA, physically durable protected floor, real FSA first-use issuance/consumption, real scientific dispatch or continual autonomous selection, external randomized policy logs, causally justified gain-per-compute savings, sealed science acceptance, two unattended fresh generations or physical-fault/24h-soak evidence. F1/F2 already consumed; never rerun them.

**R6 operational prerequisite:** independently provision and qualify a protected FSA external floor and signing identity (issue #20), implement its atomic FSA-owned first-use writer and issuer *without giving Dream-RSI CAS or dispatch authority*, validate failures physically, then qualify signed and first-use-protected FSA → primary → archived results → next experiment succession. A policy may influence the selection; only the separate FSA can authorize and execute. This is the path from a source-only optimizer to an active autonomous scientific system, not a production cutover at R5.
