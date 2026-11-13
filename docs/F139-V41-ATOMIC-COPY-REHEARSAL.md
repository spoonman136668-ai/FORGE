# F139 V41 copied-ledger atomic escrow/source-transition rehearsal

## Scope

This is a source-only rehearsal route for the original FORGE F139 V40 to V41
recovery. It does not install, pause, resume, or restart the running original
Windows controller. It does not mutate issue #1715, issue #807, any original
owner ledger, a GitHub ref, a runner, a scientific dataset, or a model.

The V41 event verifier and source-transition verifier are already qualified
in merged PRs #1722, #1725, #1726 and #1727.

## Distinct implementation

The new module `f139/nci04_v41_atomic_copy_rehearsal.py` uses the existing
owner-mutex identity and a query-only original SQLite connection, obtains a
fresh authenticated cold-copy receipt and a source/pending-issue bound
canonical owner-comment comparison, then makes an isolated *new* SQLite copy
via the SQLite online-backup API. It never writes to the original.

The copied ledger must match the exact old original head. Under its separate
copied-file mutex and one `BEGIN IMMEDIATE` transaction, the writer:

1. Rechecks source, original head, two issue identities, cold-copy receipt,
   owner intent and absence of previous escrow.
2. Appends the canonical `NATIVE_PENDING_ESCROWED` record for #1715.
3. Constructs the original-history V41 source transition proof, binding the
   escrow SHA as the immediately preceding append-only event.
4. Updates the copied `meta.source_sha`, then appends the exact source-v36
   event. The existing `Database.verify()` validates the entire result
   **before** the SQLite transaction commits.
5. Reopens the copied database cold and verifies the resulting exact head;
   rereads the original query-only head and asserts no original mutations.

Synthetic failure-injection controls deliberately raise after escrow, after
the transition append, and after verification but before COMMIT. Every case
must leave the copied source, head and event rows unchanged after rollback;
the original must remain untouched. Other tests deny unlocked copy, same
original path, forged owner scope, wrong pending issue and bad backup hashes.

## Evidence separation

The synthetic tests mock original-history source proof construction where
that proof requires the real 1,826+ original events. They exercise genuine
SQLite BEGIN/ROLLBACK and SHA-chain appends, not a real original-host
qualification. The unchanged full original source-regression suites continue
to exercise source and replay verifiers. Do not describe synthetic tests as
an accepted live cutover, recovery, model learning, or scientific result.

A real owner operation remains blocked until all these *separate* facts
have been authenticated on the actual Windows owner: full cold backup
restorability including provider archives and generation binary; physical
owner SID, task definition and lease; current original SQLite head;
unadmitted #1715 immutable source/PR; owner comment and independent release
approval; exact release ref/build; and authorized same-task transition.
Even after copied-ledger rehearsal passes, no real source transition route
is introduced by this patch.

The implementation has no CLI, GitHub POST, workflow dispatcher, new
controller, queue, scheduler, paid API, Hybrid admission or scientific
first-use capability.

## Cold-reopen orphan rejection

`Database.verify()` also calls the V41 escrow completion auditor. When a
source-bound escrow exists without the immediately following v36 transition,
the database is rejected on every post-commit or cold read. Only a provisional
escrow at the exact live head, within the *same writable SQLite transaction*
under the copied-file owner mutex, is allowed while the existing source proof
is constructed. An unrelated intervening event, wrong source/comment/escrow
SHA, or a second escrow fails closed. This changes no live writer or owner
transition route; the old source without an escrow is unaffected.


## Sealed original-backup to copied source-replay seam (DEV only)

`rehearse_from_sealed_cold_bundle` now joins the **existing** independent
offline V41 manifest verifier to the **existing** exact original-owner
read-only and copied-ledger atomic rehearsal. It requires a sealed manifest
bound to the **same** target candidate SHA, the identical original source
and ledger head, the canonical run ID, and a fresh authentic owner-comment
identity that the existing copied-rehearsal verifier must independently
authenticate. It derives the copied-rehearsal backup hash only from the
digest-verified sealed manifest, not from an operator-provided loose SQLite
filename or inferred file path.

Both historical failed-provider ZIPs, generation executable, provider
archives and SQLite are verified by the existing independent restore before
any copied transaction. A second original/backup comparison occurs inside
`rehearse_locked_original`. This wrapper only writes through the existing
isolated **copy-only** route; it cannot update original SQLite, install a
release, alter the existing owner task, create a ref, update #807, admit
#1715, authorize scientific first-use, or approve Hybrid.

The original Windows success on run `43396349980` sealed a recovery bundle
against target `616b87b01c8abd37ee0e0a2d5b5571c51272ba9e`. It is
valid **historical recovery** evidence; it is NOT automatically an
approval or same-target release rehearsal for later `main`
`bb0a74d434c78266f1fd8b9388024d29f2f63ee1`. A later candidate
needs its own source-bound release qualification and independent owner intent.
No such actual live transition or owner approval is made by this module.

The added synthetic interface tests mock ONLY the already independently
qualified sealed restore and owner-intent/copy stages to test binding,
wrong-target refusal, missing-approval refusal, manifest tamper and owner
immutability. They do not assert a genuine owner or scientific result.
