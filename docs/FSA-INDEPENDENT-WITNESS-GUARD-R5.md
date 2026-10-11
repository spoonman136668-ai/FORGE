# FORGE FSA R5: rollback-resistant witness guard (source-only)

Parent: draft PR #15 exact commit `5e43156d740b6896d5d9466b68961c7a682c80f9`. Bounded delta: `fsawitnessguard/guard.go`, `fsawitnessguard/guard_test.go`, and this document.

## Purpose

An independent signed witness is not enough to reject rollback if a storage snapshot restores an old but correctly signed statement. This isolated witness guard compares the signed statement with an **independently retained exact high-water commitment** comprising a monotonically increasing revision and domain-separated digest of the complete signed witness.

The guard provides a read-only `ReadHighWater` adapter for `fsaservice.WitnessReader` and a one-successor conditional update with two independently supplied interfaces:

- `Ledger`: durable atomic compare-and-swap of the signed witness by exact previous digest.
- `Floor`: *physically independently held*, rollback-resistant conditional-write register of the monotonic high-water commitment.

The caller must supply externally authenticated trust pins and separately provisioned ledger/floor resources. **This package does not provision either backend, generate credentials, sign statements, authorize scientific transitions, start services, or establish physical independence.** Mock in-memory backends are used only in tests.

## State transitions and fail-closed behavior

1. Read signed ledger witness; validate its domain, immutable archive/key/epoch/binding identity, public-key pin, revision, head and independent Ed25519 signature.
2. Read the separate floor; require exact revision **and digest match**. A lower/higher floor, valid-but-stale signed ledger, different digest at the same revision, offline floor, forged signature, or identity drift blocks reads.
3. Require a caller-supplied expected current witness and an independently signed successor advancing exactly one sequence and one revision with a changed head.
4. Perform **one** ledger CAS. Definitive conflicts return no success; indeterminate errors halt without replay.
5. Perform **one** independent floor CAS. A failure or uncertain result halts without replay; the ahead-of-floor ledger is unservable until independent recovery evidence is established.
6. Verify exact independently committed readback before declaring success.

There is no automatic replay after a write might have committed, no local-floor fallback, and no permission to repair or rewrite a durable authority record. Explicit independently verified reconciliation is a separate future requirement; this intentional fail-closed window is not yet unattended availability.

## Qualification and remaining blockers

Test cases cover ordinary advancement, source-compatible restart, rollback of either side, forged and identity-drifted signatures, a skipped revision, external outage, conflict, ambiguous ledger/floor writes without retry, and concurrent attempts with one winner.

Source qualification must run at an immutable commit on public hosted Linux and native Windows GitHub Actions, including full `go test`, Linux `-race`, vet, build, and public source isolation.

**Not demonstrated:** production-grade atomic CAS, off-host independent floor, hardware-protected signing keys, durable write acknowledgment across power loss, authority/witness host replacement, partition recovery, authenticated physical binding, certified scientific source admission, unattended discovery/experiment execution, or cutover.

The real next milestone requires independently provisioned and verified services in separate failure domains, controlled fault injection and recovery evidence, then the full unattended FORGE progression qualification. Keep PRs #14/#15/#16 draft and isolated. CKB-plane remains the sole current execution/orchestration, qualification and acceptance authority. No deployment, live science, production runtime or accepted-ref mutations are authorized by this source milestone.
