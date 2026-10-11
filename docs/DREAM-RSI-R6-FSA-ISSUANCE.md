# FORGE Dream-RSI R6 — separate FSA-owned first-use issuer transaction

**Unactivated FSA code.** R6 adds a **new FSA-side source module** `fsaissuance`, separate from the existing Dream-RSI optimizer. It uses the pre-existing `researchlog`, `privatearchive`, `fsahead` and `fsatrust` authority interfaces rather than introducing a scheduler, new signer, live control service or additional acceptance authority.

## Issuance path

The policy optimizer remains a candidate ranker only. Dream-RSI R4's independently anchored eligibility snapshot and R5's canonical first-use plan **do not give permission to execute**. R6's FSA-owned `CommitFirstUse` requires all of:

1. An externally pinned *exact* R5 first-use plan SHA and FORGE FSA trust identity; valid source/prereg/cohort/witness/lane/run and frozen budget are inherited from R4/R5.
2. Stable `fsatrust.Recover` from an **independently provisioned** authority. R6 rejects missing/mismatched protected FSA archive binding, external head changes, untrusted signing identity, archive rollback, inconsistent or missing original evidence, or stale plan.
3. Independent recomputation of precisely one projected STARTED record from the **current** complete FORGE private archive, exact sequence and SHA of the frozen plan.
4. An independently owned `Issuer` capability that must revalidate the source/prereg/cohort and eligibility under its own FSA authority and return a signed certificate. The optimizer contains no signing keys or issuer implementation. Certificates signed by any key other than the separately pinned FSA key, or for any other checkpoint record/head/epoch, fail **before** a journal write.
5. One exclusive-create FORGE journal STARTED append. A competing writer loses rather than replacing a record. A partial/error write marks the original **consumed or unknown**, and cannot be restarted automatically.
6. **Exactly one** `fsatrust.Advance` that validates the actual archive, independently pinned signed certificate and external high-water, performs one remote CAS, then authenticates its readback. Any uncertain, denied, interrupted or conflicting CAS must not be replayed; a locally written STARTED retains its irreversibility.
7. A separate `fsagate.ProveFSAFirstUse` read-only reconciliation of the pinned plan, signed original STARTED and independent high-water. The resulting `FirstUseConsumed` and `FSAFirstUseCommitted` booleans document only consumption, never permission to dispatch or scientific acceptance.

`ReconcileCommittedFirstUse` uses **only read calls** following uncertain commits and never issues another checkpoint or original. The same original run ID/cohort cannot be consumed twice. A successful source test does not supply an independent trust domain.

## Important limitations

- The production `Issuer` is **an interface, deliberately without a live implementation**. CI tests use a deterministic, in-process signing fixture and a simulated external CAS. These tests do not supply physically protected key custody, cloud resources, real fault domains or independently witnessed monotonic first-use.
- While this Go module composes the issuance transaction, its independently trusted signer must itself validate **actual authorized FSA eligibility**; it cannot merely sign caller-provided bytes. No runtime issuer/capability has been installed. Review/plan identity is revalidated on the FSA archive pre-append and again through the external CAS.
- Issuer/authority failure before the local STARTED write returns **denied**. Any failure once a STARTED write is attempted returns **uncertain consumed-or-unknown**, including a CAS rejection. Never treat a failed CAS as restoring a cohort's eligibility.
- A local append and remote CAS are not a single physical transaction. An intermediate crash can strand a STARTED record before protected CAS. This deliberately **fails closed without replay**, and requires FSA-controlled independent recovery. R6 does not claim that a physically atomic two-system commit problem has been solved.
- After a certified first-use the return value still has `DispatchAuthorized=false`, `ScientificAccepted=false`, `AcceptedRefMutation=false`, `PhysicalIndependenceDemonstrated=false`. Separate FSA original-launch authorization, immutable raw evidence collection and scientific acceptance remain future qualified authority functions.
- No changes to CKB-plane, KTRADE, Wingless/Yggdrasil originals, prior outcomes, FSA live deployment, or existing scheduler. F1 and F2 remain scientifically consumed.

## Deterministic qualification

Run on Linux and native Windows at an exact immutable source tree, with focused regression + one full Go regression, vet/build and Linux race:

```sh
go test -count=1 ./fsaissuance
go test -count=1 ./...
go vet ./...
go build ./...
go test -race -count=1 ./fsaissuance
```

The tests cover: separate Wingless/Yggdrasil FSA setup; a valid FSA first-use exactly once; consumed proof without dispatch; issuer denial/forgery/wrong head; FSA outage and stale plan; CAS denied after archival STARTED (no replay); CAS committed but response lost (read-only reconciliation with no repeat CAS); and a two-writer race. **All are in-process mocked-service tests**, not real FSA infrastructure or real scientific experiments.

## Remaining prerequisites before operational science

[Physical FORGE FSA gate #20](https://github.com/spoonman136668-ai/FORGE/issues/20) still requires three actual, independent and operator-approved failure domains; independently protected signing keys and retention; atomic, durable monotonic CAS under actual partitions/power failure/host replacement; and independently retained raw witness evidence. No cloud provider has been authorized or connected for provisioning. The separately qualified operator-owned FSA signer and scientific eligibility issuer must then be implemented, proved under real faults and coupled to FSA-owned original execution authority (never the optimizer).

Only then can the system qualify FSA-authorized science → first use → immutable results → next Dream-RSI policy iteration → independent scientific acceptance. Prove two fresh **unattended** lineages, temporal randomized-policy validity and sealed independent holdout gains, and a 24-hour fault/restart soak before authorized activation.

**R6 status on source qualification:** FSA issuance *logic and recovery contract* only, not deployed or operational FSA. No experiment starts from these tests. No claimed real discovery gains.
