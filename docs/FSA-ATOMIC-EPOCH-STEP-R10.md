# FORGE FSA R10 — owner epoch + one-shot step journal (source-only)

**Status:** source-only/synthetic qualification; **not deployed FSA authority, old-owner revocation proof or permission for worker execution**.

## Operational gap addressed

The preceding R8 worker step interface required a separately authenticated, linearizable authority to enforce **both** current owner epoch and globally unique step consumption in the *same atomic operation*. R9 retained independently signed step receipts, but that retention is not an epoch/consumption authority.

R10 introduces `fsaepochstore.Store`, an explicitly bounded FORGE-only **single-writer local prototype** with a single append-only journal for:
- `TRANSFER`: strictly increasing owner epoch, changed FORGE owner identity, independently signed transfer authorization from a separately pinned Ed25519 transfer root; replay and previously used transition nonces rejected.
- `STEP`: one-shot globally unique step SHA, correct owner/epoch and immutable archive head, lane, original ID, intent SHA, pinned worker binary SHA, monotonic worker lease sequence and expiry verified using a separately supplied trusted clock. A separate signer produces an Ed25519 step-receipt **before** the one immutable atomic journal record is created and fsynced. No signer/private key is bundled.
- Every recorded transition and consumed step is fully revalidated on every read/restart. The canonical receipt log forms a chained, strictly numbered immutable history. Unknown files, holes, tampering, signed identity drift and rollback below a separately pinned minimum ordinal fail closed.
- A mutex serializes in-process read, transfer and step operations; exclusive filename creation rejects racing cooperating processes. Ambiguous creation/signing results poison the instance, prohibiting blind retry.

The single journal closes the **local** gap where revocation and step consumption were separately stored and could disagree. In particular, a transfer and a concurrently proposed step cannot both be accepted against a stale in-process owner state.

## Integration evidence

The `fsaservice` test drives `workerfence.InspectStep` through the existing **two authenticated mTLS authority/witness servers** and an R10 store signed by separate synthetic transfer/step signers. It verifies a first one-shot consumed step, denial of replay, monotonic signed owner transfer, denial of a revoked owner, and denial of a newly transferred owner until the independent remote FSA epoch/witness also changes. The store restarts with externally pinned minimum ordinal and retains the transfer.

Focused negative qualification also covers invalid signer, skipped epoch, reused/non-FORGE owner, invalid binary/head/lease, absent clock, expired step, lost signature response, concurrent same-instance and cross-instance consumption, corrupted records, symlinked entries, valid-tail rollback, and process poison.

## Still absolutely blocked

This is **not** yet a physically protected/independently deployed monotonic FSA backend. Neither local directory + O_EXCL, process mutex, hash chain, Ed25519 receipt, nor externally *claimed* minimum ordinal proves true multi-host linearizability or withstands privileged whole-volume rollback. Clock, signer, remote trust, storage/access control, crash/power-cut durability and old-owner revocation remain deployment responsibilities. The test fixture cannot attest CKB-plane has relinquished ownership. It does not execute scientific steps.

Before activation, the independent deployed FSA must own an atomic, externally witnessed **epoch+step commitment** across runner nodes and must mediate actual worker side effects under an enforcement protocol immune to read/consume/act timing gaps. Immutable original-first-use custody, CKB cutover signoff, two-lane recovery tests, research budgets, negative/evidence integrity and full qualification still apply.

No KTRADE/CKB-plane service, credential, queue, scientific experiment or accepted reference is mutated.
