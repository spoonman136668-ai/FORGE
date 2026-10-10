# FORGE — direct private Mind-Palace read-only integration

**Current scope:** Qualified code is an offline/transport adapter, **not a
deployed FSA, background synchronizer, research dispatcher or memory writer**.

FORGE's `mindcontext` package can fetch small, provenance-bearing advisory
context directly from the private Mind-Palace repository, **without depending
on CKB-plane's mailbox/controller/queues/runners**.

## Read path

1. A privately configured FORGE runtime supplies a **fine-grained GitHub token
   restricted to the private Mind-Palace repository, Contents:read only**.
   Token bytes are never committed, logged, placed in public Actions secrets,
   or passed into unrelated workers. No real private credential is used by
   the public qualification workflow.
2. `NewGitHub(token, client)` creates an outbound **GET-only** transport
   fixed to `api.github.com/repos/spoonman136668-ai/Mind-Palace`. It forbids
   redirects, arbitrary paths, mutable file ref, non-base64 file responses,
   oversized bodies and Git blob identity mismatches.
3. `Reader.Read(ctx, projects, maxRecords)` resolves Mind-Palace `main`
   exactly once and fetches the three published remote data files at that
   **same exact 40-character commit SHA**:
   - `.ice/remote-bootstrap.json`
   - `.ice/remote-catalog.json`
   - `.ice/remote-index.ndjson`
4. Validate schema IDs, `direct-repository-read` transport, catalog ranges
   and equal `source.records_sha256` values. A mismatch or unavailable file
   blocks the operation. The records fingerprint is a consistency check, not
   cryptographic verification that the underlying raw records are authentic.
5. Retain mandatory global governance, then select bounded, round-robin
   research context only for `Wingless`, `Yggdrasil`, and `Research`.
   CKB-plane, KTRADE, and unrelated/private projects are explicitly excluded.
   Require current/confirmed/observed status and original `source_refs`.
   Any record with mismatched project, missing provenance or invalid JSON
   blocks retrieval.
6. Return a `forge.mind-palace-context.v1` **advisory-only** result containing
   the pinned commit, records checksum, selected record IDs, statements,
   `source_refs`, and deterministic output SHA. The caller must independently
   verify original sources for any scientific/acceptance decision.

### Operational limits

The GitHub REST Contents API transfers **the full generated index file**; this
implementation selects and returns only the specified catalog line ranges,
with a strict one-megabyte raw transfer cap and 16-KiB total selected output
cap. This is NOT a server-side range read. A future authenticated ranged index
transport can improve network efficiency without widening context visibility.
No full index contents enter the result or public GitHub Actions logs.

A `Read` invocation itself is synchronous, bounded and **read-only**.
It cannot set scientific thresholds, alter a frozen preregistration, authorize
FSA science, ingest knowledge, checkpoint Mind-Palace, enqueue work, or access
KTRADE execution resources.

### Next integration gates

Before a live FORGE controller consumes this adapter: privately configure
read-only GitHub credentials through the designated FORGE-only secret store;
independently qualify private connectivity and observe exact actual source
refs; test credential denial, rate-limits, revocation and rotating `main`
between reads; and ensure source text cannot act as executable instructions.
Record the pinned source identity in the FORGE private scientific archive.

FORGE documentation proposals still require Mind-Palace's established
**private, separately authorized classification and checkpoint**. A read-only
retrieval **does not** authorize background memory updates.

**Hard constraint:** no FORGE credential, runner lease, storage path, controller,
queue, scheduler or scientific acceptance authority may be shared with KTRADE.
