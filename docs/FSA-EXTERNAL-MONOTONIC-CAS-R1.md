# FORGE external FSA checkpoint authority — compare-and-swap boundary R1

**Status:** source-only, **NOT a deployed monotonic trust service**. This
package specifies and tests the independent write boundary for FORGE's
scientific history. There is no active FSA signer, controller, private key,
trusted state server, research dispatcher, production credential or
Mind-Palace writer in this public repository.

## Why this is separate

FORGE's `privatearchive` holds original scientific records. The
`fsahead` verifier cryptographically checks FORGE-only signed archive
heads. Neither a hash chain nor a public signed receipt can stop a
privileged attacker from rolling back **both** an archive and a local
checkpoint file.

A separately controlled **FORGE-private monotonic authority** must store
the previously accepted head independently of the archive and all research
workers. It must be authenticated, linearizable and durably
compare-and-swap (CAS) the trusted head, including across crashes.

The `fsatrust.Authority` interface requires:
- `ReadAnchor(ctx)`: independently authenticate an FSA-controlled anchor
  containing archive identity, key ID, Ed25519 public key, epoch, last
  accepted record sequence and SHA256;
- `ConfirmArchiveBinding(ctx, archiveID)`: verify that archive ID is
  provisioned for the correct **physical** FORGE-private archive, not a
  caller-supplied path or an arbitrary copy;
- `CompareAndSwap(ctx, old, next)`: persist exactly one monotonic
  transition atomically, conditional on the exact previous trusted state.
  A client must treat any timeout or error as **possibly committed**.

No production implementation of this interface is present yet.
Unit tests use an intentionally in-memory synthetic authority. They
exercise the API's fail-closed behavior, **not** external durability or
real-world protection against server compromise.

## FORGE-only acceptance sequence

1. Privately provision immutable FSA identity from independently verified
   operator authorization. Do not acquire trust from the candidate receipt,
   Mind-Palace, CKB-plane or a worker.
2. `Advance(ctx, backend, archive, identity, signedHead)` loads a fresh,
   authenticated, pinned anchor and explicitly checks its physical-archive
   binding.
3. It validates the signed FSA payload with `fsahead.VerifyArchive`,
   including identity/epoch, exact predecessor, retained raw evidence,
   source journal continuity and full new head.
4. It performs a single external CAS and reads the trusted state back
   before returning success. A failed CAS means conflict; a failed/ambiguous
   CAS/readback means **indeterminate**, requiring recovery before action.
5. `Recover(...)` is **read-only**: load the independently authenticated
   high-water mark twice, verify both agree, verify full retained archive
   record count/head and every referenced original terminal artifact.
   It never rewrites, resets, replays, retries, launches or schedules a
   scientific primary.

This boundary does not confer science admission or accepted-ref
promotion. One-shot primary dispatch, preregistration, frozen controls,
separate authority signatures and original STARTED receipt evidence
remain mandatory in later qualified stages.

## Hard isolation policy

The FSA trust service, archive, queue, runner leases, credentials, key
custody and resource budgets must belong **only to FORGE**, outside the
installed CKB research controller and outside KTRADE's execution domain.

It is forbidden to reuse a KTRADE account, broker token, runner lease,
scheduler principal, service account, queue, production authority or
settlement database. All live KTRADE activation remains separately
authorized, and paper-only status is preserved.

Mind-Palace remains a separately credentialed **read-only advisory**
context source. Its governed private ingestion/checkpoint is distinct
from FORGE's FSA authority.

## Remaining safety and integration gates

- Provision a genuine private FSA signer and **off-host/off-store
  authenticated monotonic CAS** service with access-control verification,
  atomic durability guarantees and audit witnesses; credentials must
  never enter public GitHub Actions.
- Prove stable physical-archive identity, key rotation/epoch transition,
  independent rollback detection, cross-restart readback, concurrent
  writers, uncertain commit reconciliation and service outage handling.
- Add immutable original STARTED witnesses, explicit FSA-only execution
  authorization, crash-cut tests and a restricted private FORGE runner
  pool with bounded resources.
- Qualify simultaneous existing CKB and KTRADE activity with zero shared
  write authority or disruption before any FORGE runtime activation.
- Follow exact source identity, focused tests, Linux race, native Windows
  tests and complete integration regression. Preserve all negative,
  mixed, invalid and indeterminate scientific outcomes.

**Until these gates pass, only source-only tests and no live research
execution are permitted.**
