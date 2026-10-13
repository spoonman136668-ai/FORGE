# FSA R9 — independently signed step receipt custody storage (source-only)

**Status: inactive source-only storage primitive. It does not implement the atomic external step authority or enable science.**

`fsastepcustody.Store` retains only already-authenticated, domain-separated Ed25519 worker-step receipts (R8) in a new `forge-fsa-step-custody` directory. This directory must be physically and administratively isolated in any future deployment; a temporary local test directory does not provide that isolation.

- Caller supplies a pinned independent step receipt **public key**. Neither production signing keys nor a signer are provided.
- Receipts bind the exact authority head, lane, original experiment, intent digest, owner/epoch, worker ID, executable digest, lease sequence, expiry and step SHA. Invalid signatures, foreign original identities and changed worker binaries fail closed.
- Each step claim is stored under a deterministic content-addressed name with exclusive create, canonical record checksum, file sync and best-effort platform directory sync. Exact duplicate claims cannot be replayed into a second record.
- Each read/restart validates the full receipt directory, structural bounds, canonical encoding, cryptographic provenance, and key-to-body identity. Foreign entries, holes, symlinks and corruption are blockers, not reasons to delete or silently rebuild.
- Open requires an **external minimum completed-record count** and a pinned public key on every restart. A live store also remembers the highest count it saw, and poisons its own instance on storage regression or uncertain write. A separately pinned count can detect full valid-tail deletion; the count is not itself an authenticated high-water witness.

Qualification includes both existing lanes, restart, duplicate/racing writes, forged signatures, tampered worker binary, canceled writes, foreign paths, corruption and rollback floors.

## Required separation

A local retained signed receipt is NOT proof that a separate FSA authority atomically checked live epoch revocation, lease expiry, original first-use and global step consumption. It cannot grant permission to execute an action, cannot prove that the externally pinned count is current, cannot prevent a privileged full backup rollback without separate authenticated monotonic high-water, and cannot make two machines linearizable. R8 `workerfence.StepAuthority` remains an unimplemented independently durable backend contract; this store is a separate proof-retention primitive, **not its implementation**.

No production service listener, scheduler, signer, runner, broker, KTRADE or CKB-plane mutation, Mind-Palace write, accepted-ref operation or original scientific execution occurs. The mandatory next gate is off-host provisioned, epoch-fenced atomic consumption with qualified crash/restart and worker side-effect mediation.
