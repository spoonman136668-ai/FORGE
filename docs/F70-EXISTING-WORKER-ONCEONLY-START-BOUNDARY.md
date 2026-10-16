# F70 — Existing-Worker first-use at-start transaction (NOT DEPLOYED)

## Purpose

Qualify the execution-boundary transaction on the already selected Cloudflare D1 first-use schema **without modifying the real Worker or producing scientific originals**. F69 already projects the one canonical R41 owner-and-witness signed predecision and both research lane snapshots into an inert D1 claim tuple. F70 adds source code for consuming that exact tuple **at the would-be original-start boundary**, using one D1 parameter-bound INSERT and the R35/R38 immutable, globally monotonic replay guards. A lost acknowledgement, a duplicate request, conflicting lane/epoch or any SQL error cannot yield start permission or a repeatable bearer token.

The new `d1retention/f70_worker_onceonly.mjs` is **not deployed**, exports no Worker `fetch` handler, does not call an executor and is never invoked by a live controller. It uses Cloudflare Workers' D1 `prepare().bind().run()` API shape, and reuses the existing R41 signed predecision's exact Go-compatible JSON and owner/witness Ed25519 signatures. No new signer, signature domain, controller, FSA or credential is generated. Its synthetic-positive test consumes a record in a mock database only and explicitly returns `reusable_bearer_permit_issued=false`, `external_worker_invoked=false` and `scientific_result_accepted=false`.

**Important admission boundary:** The four external preconditions in the source API are injected into test fixtures, not independently derived from a protected real CKB science owner. Calling code must never treat caller-provided booleans as proof. There is currently **no production caller with independently authenticated current-owner/dual-lane cohort custody, protected-main OIDC-bound worker identity and recovery checkpoint**. Do not connect this function to a public fetch route, supply these booleans from an HTTP request, publish its mock credentials as trust pins, or enable it in the existing Worker. Live deployment requires replacing these test-only preconditions with a real authenticated existing-owner verification at the trusted Worker boundary and a worker-side execution fence, not merely setting them to true.

### Authenticated original and Cloudflare limitations

- CKB-plane actual native engineering controller is alive, authority `plane`, generation 6; the F66 four old unfinished engineering attempts have accepted work orders and verified queue receipt hashes. Engineering queue receipt evidence is NOT a complete Wingless/Yggdrasil scientific seed first-use ledger.
- F67/F68 verified real public Wingless/Yggdrasil continuation and archived original workflow metadata. Pending Yggdrasil proxy pumps are transport, not original-science attempts. Yggdrasil continuation failed on included Codex usage limits; do not buy paid API or resubmit a possibly consumed original.
- Source-only R41 signed predecision and F69 both-lane snapshot correspondence PASS, but synthetic owner key signatures and hashes do **not** prove physically independent signer custody or complete real current seed/lease high-water.
- Authenticated live Cloudflare R39/F62/F69 preflight confirms exactly one existing Worker/D1 binding, six originals and seals, a Time Travel bookmark and **NO installed R35 atomic preuse table**. Bookmark availability is not a privately retained independently restore-tested backup. Time Travel checkpoints are time-limited; no destructive live restore was attempted.

### Acceptance

GitHub-hosted exact-head tests: F70 Ed25519 R41 source hash/signature, missing real external admission requirements, tampering, absent table, replay, D1 unknown commit/failure and no-permit result; F61 signed-workflow identity negative tests, F62/F63 local D1 crash/monotonic tests, F69 existing owner-to-R41 source integration negatives, focused R35/R38 tests, one full FORGE Go regression, vet and build. Repeat read-only authenticated Cloudflare Worker+D1 preflight, verify archives and bookmark capability. No Cloudflare mutation, no original attempt, no live worker request.

### True next operation

Obtain genuine **current** CKB scientific owner authority, including independently pinned owner identity and source/epoch, a complete trustworthy Wingless/Yggdrasil consumed/active/uncertain original/seed ledger and explicit approved fresh experiment budget. Privately qualify a recoverable D1 checkpoint (not a publicly uploaded bookmark), install R35/R38 exactly once with recovery, and integrate an authenticated protected-main OIDC / canonical owner predecision verifier with the existing science worker. Only then can the at-start D1 claim become an actual once-only execution permit. An R35 INSERT alone is a consumed intent, **not** permission to run science.

No new controller, separate signing credential, paid API, ordinary Codex PR review, KTRADE production change or interference with parallel research.
