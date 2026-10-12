# Existing Wingless/Yggdrasil lane takeover — implementation gate R1

This increment builds a read-only, cryptographically verified custody **preflight**, not an authority or runtime activation. The intended destination is the **existing Wingless and Yggdrasil programs**, preserving their source lineages, frozen cohorts, spent budgets, journal identities, negative results, pending work and one-shot original starts. FORGE MUST NOT create replacement scientific lanes or silently replay original experiments.

A separately trusted evidence collector must sign one exact source/custody snapshot for each existing lane. The collector's provisioning, CKB-owner quiescence and lease revocation, independent durable FSA authority/witness services, original queue transfer, archival import authentication and actual runner execution are **not implemented** by this PR. Signed observations alone do not revoke CKB execution capability.

`lanetakeover.Preflight` verifies exactly two stable lane identities, source commit SHA, old queue ID, old lane ID, old authority ID, signed custody records, external release evidence digests, absence of active leases or uncertain dispatches, independent per-lane custody digests and monotonic minimum sequence. It is deliberately deterministic and side-effect-free.

## Required sequential acceptance before actual cutover

1. Read and reconcile real existing CKB lane journals, lease owners, consumed cohorts, pending original starts, and all historical negatives; verify exact immutable source and provenance, without revealing private data in public CI.
2. Freeze **new** original dispatch through the existing CKB authority only after all its in-flight work has a terminal or reconciled state. Do not spawn replacement lanes and do not stop unrelated KTRADE or CKB work.
3. Independently witness quiescence and durable custody; provision separate private FSA authority, monotonic witness, isolated queue/lease persistence and exact-work-order runner access. New infrastructure must bind to the **same underlying existing programs**.
4. Qualify crash, restart, timeout, duplicate dispatch, stale signatures, split-brain owner, lost receipts and retained negative results on Linux and Windows. One final full regression required.
5. Verify old owner can no longer dispatch **these two** lanes before activating FORGE ownership; never allow two concurrent writers. Reconcile unknown outcomes without re-running originals. A controlled rollback must preserve consumed cohorts and terminal records.
6. Run the authorized live trial: each existing lane completes two genuine consecutive experiment cycles, including independently observed starts, raw terminal evidence, next-experiment selection and one unattended handoff. A passing CI job is not proof of this outcome.

The new package performs step 1 *preflight validation only* when supplied genuine externally authenticated custody records. No trusted collector key, signature or release digest is hardcoded in production; test keys are fixtures. No GitHub workflow added here starts experiments or triggers security reviews.
