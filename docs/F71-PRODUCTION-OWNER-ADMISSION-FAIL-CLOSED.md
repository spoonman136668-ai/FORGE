# F71 — Real owner-custody release is unprovisioned: remove caller-boolean bypass

## Purpose and actual engineering

F70 proved an isolated **synthetic** Cloudflare first-use claim could be recorded using four booleans supplied by the caller and owner/witness keys supplied with the claim. Those flags were explicitly described as test-only, but if copied into a deployed Worker route, any caller could set them true and substitute keys, potentially *irreversibly consuming an original-intent identifier* without authentic scientific owner approval. This is not acceptable for live autonomy.

**F71 closes that unsafe public path.** The exported `onceOnlyClaimAtWorkerStart()` now always denies **before reading or writing D1**, even when supplied all four optimistic flags and a synthetically valid dual-signed R41 decision. The previous contract is available only as explicitly named `simulateOnceOnlyClaimAtWorkerStart()` for isolated tests; it is **not a live Worker handler or an execution permit**. Future real deployment must add a trusted, independently authenticated real current-owner issuance and complete both-lane original-seed lease census before any production claim can be consumed; it must not reconnect the synthetic simulation to an HTTP caller.

## Live read-only Cloudflare evidence

The F71 qualification additionally queries the **actual existing deployed Cloudflare Worker version and D1** using existing GitHub-held Cloudflare credentials, without making changes. It reuses previously verified Cloudflare helpers to require one serving Worker version, one D1 binding, exact historical archive schema and six original+seal rows, and to inspect existing R35/R38 table and trigger names. It also checks D1 Time Travel bookmark access **without persisting/logging the bookmark or calling restore**.

Cloudflare documents that the D1 export endpoint can temporarily block live D1 queries, so F71 **deliberately does not initiate an export**. A Time Travel bookmark is not a durable private, independently tested recoverable backup; do not claim otherwise.

The authentic live database currently has no `forge_original_preuse_claims` table, current protected-main owner/epoch/custody signer, complete Wingless and Yggdrasil consumed/active/uncertain first-use ledger, independently verified private restorable checkpoint, or Worker execution-permit integration. The safety report can verify Cloudflare deployment identity, but flags all of these release/ownership/dispatch conditions **FALSE**. If the schema unexpectedly changes or a migration is only partially present, the read-only gate fails closed instead of attempting repair or a retry.

## Acceptance and isolation

Run exact-head F70 public-entrypoint denial/adversarial tests, F71 source-negative tests, existing F61/F62/F63 replay negatives, current R41/F69 owner/lease Go tests, one complete FORGE Go regression/vet/build, and live read-only Cloudflare check with non-secret content-addressed report artifact. No production D1 export, table installation, restoration, controller or science worker invocation; no research original, no extra credentials, controller, FSA service, scheduler, Codex auto-review or paid API.

## Next operational clearance

The remaining dependency is real, not synthetic: the **existing authorized scientific owner** must make available a current verifiable original predecision/epoch with a complete independently pinned present-time two-lane first-use lease high-water. Recoverable private Cloudflare custody and a trusted protected-main OIDC worker route then have to be qualified before enabling the permanent at-start D1 transaction. No unknown or already consumed original can replay. This is not achieved by setting admission booleans, a self-signed synthetic owner record, or a GitHub CI PASS.

The last known CKB engineering controller heartbeat was fresh, but its work-order leases were **not** independent original-science custody. Existing Wingless/Yggdrasil research continues separately; all changes remain on a draft FORGE engineering branch.
