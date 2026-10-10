# FORGE FSA — independently authenticated archive-head checkpoints

**Status:** Source-only cryptographic verification component. Not deployed;
no active FORGE Scientific Authority (FSA) signer, controller, secret store,
scientific execution, automatic checkpointing, or production admission exists.

## Security purpose

The existing FORGE private scientific archive validates local record
structure and chain linkage, but a valid trailing record could be deleted
without breaking the remaining prefix. A local file containing only a
recomputed hash or high-water mark **cannot establish trustworthy history**.

The `fsahead` package verifies **Ed25519 signatures issued by a separately
governed FORGE Scientific Authority** on the exact research archive head. It
takes an independently authenticated, monotonic **external Anchor**, not one
read from the untrusted journal or supplied by a research worker.

The signed payload includes:

- Fixed schema and **FORGE-only FSA domain separator**; CKB/KTRADE
  identity never qualifies as FSA.
- Externally pinned archive identity and independent signing-key identifier.
- FSA authority epoch.
- Exact predecessor sequence and SHA-256, supplied by the external anchor.
- New strictly increasing sequence and exact new journal-head SHA-256.

Both serialization and signature-message prefix are fixed in the versioned
Go struct contract. The signature authenticates the checksum and identity;
it does not authenticate unsigned experiment contents or turn historical
cohorts into fresh evidence.

## Verification path

1. A private FSA trust service provides an authenticated, immutable
   `Anchor`: FORGE-only archive ID, public key, key ID, epoch, last
   accepted sequence, last accepted head SHA.
2. `VerifySignature(anchor,signedHead)` fails closed if the domain, key,
   signature, epoch, predecessor, archive ID, or monotonic sequence differs.
   The public package exports **no signing function or private key**.
3. `VerifyArchive(store,anchor,signedHead)` loads the complete local
   FORGE-private archive, checks exact terminal sequence/head and anchored
   prior sequence/head (rejecting forks and deletion), and verifies original
   raw evidence still exists for every terminal/review/archive event.
4. It returns an updated `Anchor` **in memory only**. It neither writes a
   high-water record nor claims that the new head was durably accepted.

## Deliberate limitations

- Callers must independently authenticate and persist the anchor in
  **separate monotonic storage** controlled solely by FSA. Otherwise a
  malicious caller could roll back both anchor and archive or substitute
  its own signing key. This public code does **not** implement those
  private trust operations.
- The separately provisioned archive ID must be bound to the **actual
  physical archive instance** during eventual private controller
  deployment; passing arbitrary stores without that binding is unsafe.
- The checkpoint verifier establishes structural/referential integrity,
  not causal validity, a frozen scientific preregistration, original start
  authorization, or scientific admission. These remain distinct future
  FSA qualification gates.
- The current archive `AppendEvent` API can still write without an
  authenticated FSA intent or checkpoint. **Do not activate it as a live
  primary or production record writer.** An interruption can leave a
  partial record that must be independently reconciled rather than replayed.
- Key rotation, signed epoch transition, multi-writer durable compare-and-swap,
  remote pinned trust replication, external archival backup and complete
  crash-cut testing are not implemented and must fail closed by policy.

## Noninterference and qualification

All tests use synthetic ephemeral or deterministic fixture keys and
temporary FORGE-only archives on GitHub-hosted Linux/Windows. No real
credentials, sealed experiments, CKB private artifacts or raw Mind-Palace
content enter CI. The code only reads `privatearchive.Store`; it has
no GitHub write, trading/broker operation, process launcher, workflow
dispatcher, scheduler, KTRADE/CKB queue, runner token, or accepted-ref API.

Future privately controlled FSA admission and durability must pass exact
source identity, adverse permissions and injection tests, independent
signature validation, tail rollback, original-evidence loss, crash
reconciliation, and isolation against simultaneously active CKB and KTRADE.

**Rule:** FORGE's FSA, research controller, research archive, keys, runners
and queues remain independent. KTRADE's execution boundary is absolute.
Mind-Palace remains a separate *read-only advisory* retrieval source;
its governed update flow requires separate authorization.
