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
