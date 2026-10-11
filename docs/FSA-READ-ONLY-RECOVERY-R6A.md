# FORGE FSA R6A: read-only interrupted-update recovery assessment

Parent: source-qualified draft R5 commit `e4541756eee9958e11d0c589a769b922f350d8ff`.

Bounded delta: `fsawitnessguard/reconcile.go`, `fsawitnessguard/reconcile_test.go`, and this document. This is an **inactive source-only recovery-observation seam**, not the R6 physical deployment gate.

## Problem

R5 intentionally halts without replay if either the witness-ledger CAS or independently retained floor CAS might have committed. Previously there was no narrowly scoped way to inspect the exact attempted predecessor/successor against both independently read records without invoking a mutating recovery path.

## Implemented contract

`Guard.InspectRecovery(ctx, archiveID, previous, proposed)` verifies both exact Ed25519-signed witnesses against the externally pinned identity; requires one-step revision/sequence advancement; reads ledger and floor twice; refuses moving snapshots, outages, forgeries, unrelated digests and identity drift; and classifies only:

- `PREVIOUS_OBSERVED_NO_REPLAY_AUTHORITY`: both reads match the pinned attempted predecessor.
- `NEXT_OBSERVED_NO_ACCEPTANCE_AUTHORITY`: both reads match the exact attempted successor.
- `LEDGER_AHEAD_QUARANTINE`: ledger contains the signed successor, floor still retains the predecessor.
- `FLOOR_AHEAD_QUARANTINE`: floor contains the successor commitment, ledger still retains the predecessor.

The assessment performs **zero conditional writes, retries, repairs, signatures, queue actions or acceptance transitions**. Even a previous-observed result does not authorize replay of an uncertain write; a next-observed result does not prove scientific admission. A same-time rollback of both stores, network equivocation and genuinely distributed atomic snapshots cannot be excluded by these source checks; the independent monotonic floor and external physical trust evidence remain essential. Two consistent reads are useful diagnostics, **not** a linearizability or off-host durability proof.

## Qualification and remaining R6 gates

Public GitHub Actions qualification at immutable SHA: Linux full tests, race, vet, build and source isolation; native Windows full tests, vet, build. Synthetic tests cover no-write restart, ambiguous first-CAS commits, floor-ahead quarantine, forging, outages, unknown commitments and moving snapshots. No real host or service is provisioned.

**Still required:** separate independently controlled authority and witness hosts, third failure-domain monotonic floor, persistent key custody, authenticated immutable provisioning attestations, power-loss and host replacement tests, partition recovery, and an independently authorized scientific end-to-end admission/continuation trial.

CKB-plane remains the sole existing execution/orchestration, acceptance, deployment and runtime authority. Do not merge, activate, or use this assessment to bypass scientific gates or automatically resume an uncertain CAS.
