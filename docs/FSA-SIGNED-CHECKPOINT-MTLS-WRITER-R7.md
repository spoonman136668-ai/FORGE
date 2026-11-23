# FSA R7 — isolated authenticated signed-checkpoint HTTP write boundary

**Status:** source-only handler and synthetic end-to-end mTLS tests. **No service is deployed, no writer principal is provisioned, and FORGE scientific execution is not activated.**

## Implemented

- `fsaservice.SignedCheckpointHandler` is a standalone **unregistered** handler at POST `/v1/fsa/signed-checkpoint`. It is **not** added to existing read-only FSA authority or witness endpoints and exposes no unsigned `/v1/fsa/cas` compatibility route.
- It requires a separately pinned **writer client certificate SPKI** distinct from the configured read-only client identity; TLS must report a verified client-certificate chain.
- It accepts at most 4096 bytes of **canonical, strict, versioned JSON** containing an `fsahead.SignedHead`; malformed/duplicate/unknown fields, noncanonical encoding, wrong method/path, missing authentication and a missing or wrong content type are rejected.
- The independently pinned FSA Ed25519 signature and full private original scientific archive are verified by the R6 `CheckpointGate`, which additionally checks independent archive-binding attestation and dual-peer signed witness continuity.
- After exactly one verified, monotonic backend CAS, an HTTP success is allowed only when the separately signed remote witness matches the committed high-water mark. A commit with no verifiable witness yields an indeterminate service error, and the source-only gate latches no-retry.
- A positive response explicitly includes `execution_authorized=false`, not permission to launch, rerun, select, promote or accept scientific results.

## Qualification

Tests exercise **real mutual TLS** over a distinct test server with different reader/writer client certificates and separately pinned signing identities. Cases include successful signed synthetic checkpoint and witness, denied reader, wrong path/method, duplicate JSON properties, forged signature, duplicate signed checkpoint, CAS committed but witness absent, and denial of repeat after uncertainty. Full Linux race/vet/build and native Windows qualification are required before merging.

**Important limitations:** A source-only handler is not an isolated, durable, permissioned FSA deployment. The positive test synchronously synthesizes an independently signed witness upon local test CAS and cannot establish physical failure-domain separation, hardware durability, signed evidence custody, atomic source authority or full old-owner revocation. Production TLS certificates, keys, signer, remote protected checkpoint, physical archive attestor, CKB interlock, worker-side epoch fence and release privileges remain unprovisioned.

No KTRADE, CKB-plane, Wingless or Yggdrasil runtime, mailbox, scheduler, original attempt or accepted reference is modified by this work.
