# FORGE FSA D1: globally exclusive, pending original first-use

**Deployment state: NOT DEPLOYED. Scientific dispatch remains DENIED.**
This is a bounded FORGE-native Cloudflare D1/SQLite single-statement writer primitive,
not a new controller, FSA signing authority, receipt service, or worker endpoint.
The existing Windows F139 controller stays sole scheduler. This source cannot
issue an original-start receipt or authorize any scientific experiment.

## Source components

- `schema.sql`: two FORGE-only tables and a global slot-closing trigger.
- `reserve_pending.sql`: one parameterized INSERT...SELECT...RETURNING statement.
  Its precondition checks exact archive identity, FSA head, owner epoch and
  **independently pinned** global ledger generation/fingerprint against the
  authority-owned state. Successful insertion atomically closes the global slot,
  preventing a second original in either lane on an unreconciled high-water.
- `readback.sql`: structural one-original readback, not independent witness.
- `test_atomic_pending.py`: real SQLite concurrent contention, cross-lane,
  stale-epoch, stale-head, stale-ledger, replay and restart tests.

Cloudflare D1 is SQLite-compatible and prepared writes are individually atomic.
Bind the nine positional arguments; never interpolate SQL. The proposed future
write-side FSA service must execute the INSERT through an existing provisioned
D1 binding, with no public endpoint or worker credentials. Do not install a
new scheduled Cloudflare controller.

A reservation returns **`RESERVED_PENDING_INDEPENDENT_WITNESS`**, not a worker
permit. No result, no row, constraint violation, timeout, disconnected caller
or uncertain commit can justify a retry or original dispatch. The global slot
can be re-opened only after a separately authenticated, independently
reconciled signed high-water and complete imported all-lane ledger, using a
separate qualified authority-only update mechanism. This module intentionally
does NOT implement that update, because without an independently provisioned
signer/witness it would be an unsafe self-authorization shortcut.

## Genuine production prerequisites (not supplied by this repository)

1. Read-only inventory and verification of the **existing authorized**
   Cloudflare account, D1 database ID, service isolation, backup/restoration
   capability, quota and independent failure domains. No credentials should be
   embedded in a GitHub PR, CI logs or ChatGPT conversation.
2. Independent pinned current FSA issuer, cohort-archive binding and separate
   Ed25519 signing identities, with hardware/operational custody evidence.
   Import the COMPLETE prior active, consumed, indeterminate and uncertain
   starts across Wingless/Yggdrasil before opening any reservation slot.
3. A single genuine independently signed frozen scientific selection, novel
   source birth, full family/consumed-ledger attestation verified with
   `fsaadmission.AssessSelectedArchived` and independently witnessed archive
   readback. A test fixture or locally generated key is NOT admission.
4. An independently retained, signed start receipt bound to the exact D1
   reservation, monotonic external high-water, owner lease and
   **worker-side side-effect fence**. Read/write/read in D1 does not provide
   independent custody or eliminate time-of-check/time-of-use races.
5. An isolated owner-controlled first original on a GitHub-hosted worker,
   crash/duplicate/partition fault tests, negative retention, independent
   result readback, and a second automatically selected source-qualified
   experiment. No automatic optimizer promotion from engineering CI.

## Reproducible qualification

```
python3 -B -m unittest discover -s fsad1 -p 'test_*.py' -v
```

The existing Linux/Windows full FORGE PR workflow runs this same test and
the full Go regression. These tests prove SQLite statement behavior ONLY,
not a remote Cloudflare D1 deployment, independent signing custody,
physical durable high-water or a genuine first-use.

## F139 additive compatibility with existing Cloudflare D1

The existing live FORGE D1 contains historical `forge_research_*` archive
objects and may contain unrelated user tables. The FSA reservation DDL uses
an exclusively `forge_fsa_*` namespace to avoid colliding with ordinary
`authority_state` or `original_firstuse` user tables. All table and trigger
names are explicit and no historical `forge_research_*` object is altered.

`test_migration_isolation.py` validates a six-original/six-seal archival
fixture with an existing foreign table, snapshots every previously installed
object and row, applies the FSA DDL, and proves preserved bytes and an empty,
closed FSA reservation state. Reapplication or a preexisting FSA namespace
must fail rather than silently reinterpret an existing table. These tests
are local SQLite compatibility only: they neither execute on the real D1
nor attest a production backup, signature, all-lane first-use history, or
start permission.

### No partial D1 schema is acceptable

A collision on a *later* trigger or table must never leave earlier FSA DDL
committed without its guards. `migration_contract.statements()` checks that
all six DDL objects exist in the exact frozen order. Production installation
must use **one atomic Cloudflare `D1Database.batch(...)`** containing all six
prepared statements, with the provider's all-or-nothing rollback on any error.
Do **not** install this DDL as sequential standalone REST calls, as an
unqualified `exec()` multi-statement script, or via a CLI whose transactional
rollback has not been independently demonstrated. D1 does not permit a manual
SQL `BEGIN TRANSACTION` in its Worker binding.

The `migration_contract.qualify_atomic_sqlite` helper is **test-only**, using
one explicit transaction against local SQLite. Its regression injects
collisions at both table names and all four trigger names and proves rollback
of the *whole* namespace while preserving all existing rows and DDL. This is
not evidence that a live D1 migration has occurred or that a future remote
caller used the required provider batch. Remote writer deployment and verified
backup/independent FSA custody remain blocked.
