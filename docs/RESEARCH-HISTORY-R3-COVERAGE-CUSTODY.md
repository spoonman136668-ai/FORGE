# Research R3 — full GitHub-visible coverage, durable retention and independent custody

**Status:** Qualification of read-only inventory plus offline retention contract. **Not** complete historical archival custody.

## Why the existing eight archive objects are insufficient

GitHub's Wingless repository listed **2,119** Actions runs and Yggdrasil listed **1,413** Actions runs at the October 14 survey. Those 3,532 runs include builds, regressions, repairs and research. They **cannot** be equated to 3,532 original scientific experiments. R1's 378 PR identities are likewise not one-to-one experiments. R2 byte-verified **eight specific original archive ZIPs**, not the complete corpus. W-F10 and Y-F9 were verified separately. Complete scientific history requires matching a canonical experiment ledger and every consumed first-use, including pre-original failures, negatives, invalids, cancelled jobs, heldouts, original stdout/stderr and repaired attempts.

## Gate A — exhaustive accessible metadata enumeration

The existing `forge-research-archive-cohort.yml` gains a **manual/PR/main-push-only** history-coverage job. It reads all pages of existing Wingless/Yggdrasil Actions run and artifact metadata using the existing read-only GitHub token. The offline `historycoverage` package produces a bounded report recording:

- exact per-lane observed and API-declared run/artifact counts and SHA-256 snapshot digests;
- every *original-named* artifact with GitHub run/source SHA/artifact identity and archive digest;
- expired/unavailable objects, malformed or absent digests, orphaned artifacts and source-head mismatches;
- explicit separate `github_accessible_snapshot_reconciled` and **always false** `full_historical_scientific_coverage_verified`.

Public Actions artifact reports are *temporary gap inventories*, not durable backups. Source code and other repositories must not be silently searched or executed to fill missing evidence. A completed GitHub run is not scientific proof. Missing history from deleted runs, expired artifacts, unknown naming conventions or older CKB ledger items remains unresolved.

## Gate B — beyond-expiration retention

`privatearchive` already has an isolated write-once store, but it is local-only and cannot prove off-host backup durability or recover from all interrupted writes. A GitHub Action's `retention-days: 90` is also not a perpetual archive.

`retentiongate` now verifies a **separately supplied**, previously archived exact original ZIP *and actually restored replica bytes*, a pinned external trust anchor, two distinct Ed25519 signing keys for research owner and external storage custodian, exact source run/artifact/digest, a monotonically anchored minimum revision and a future retention horizon. Changing source bytes, storage identity, receipt, keys, signature, revision, retention date or restored bytes must fail. The CLI does not upload, create credentials, select storage, activate a backup, or authenticate its own anchor.

**External requirements not provided / cannot be manufactured in a source-only PR:**
1. An operator-authorized private store with separate access control, retention/immutability policies, backup/restore and outage drills; do not put sealed evidence into public GitHub.
2. Actual per-original transfer before GitHub source expires, independent integrity-checked restoration and separate escrow/billing/quota policy.
3. A separately protected monotonic high-water record and pinned external public keys delivered through a trust channel distinct from FORGE's working repository and CI controller.
4. A real external custodian controlling its own signer, audit logs and revocation procedures, and an independent reviewer of full per-lane/CKB consumed-first-use history.

Offline signature verification establishes **cryptographic consistency** only. Even valid signatures and byte equality do **not** prove separate trust-domain control or regulatory-grade durability. The returned report deliberately keeps `external_trust_roots_operationally_independent`, `retention_durability_across_failures_proven`, `first_use_authenticated`, and `scientific_accepted` false.

## Gate C — independently qualified scientific custody

F3 prospective execution remains blocked unless each project's new cohort was genuinely independently originated after source freeze and separately admitted by the current sole CKB-plane authority. History inventory and backed-up older original ZIPs **cannot** establish source-birth chronology, nonreuse of all consumed seeds, cross-lane exclusivity, sole owner release, trusted first-use receipts or scientific validity.

The acceptance path after obtaining authentic evidence is: verify external source birth and pinned identity → reconcile complete CKB/Lane consumed high-water with independent custody → prove private archive restores from off-host storage → challenge rollback/tampering/duplicate starts → source-only review → authorize genuinely new original **once**, only via existing authority. No new scheduler/controller/queue, KTRADE/broker mutation or paid API.

## Result interpretation

Passing R3's tests can qualify **the monitoring and evidence contract**, not production retention or independently accepted science. Failed evidence must be categorized explicitly rather than repaired by silently replaying a consumed original. Preserve positive, negative, mixed, invalid and unqualified original results, each at immutable source/provenance IDs.
