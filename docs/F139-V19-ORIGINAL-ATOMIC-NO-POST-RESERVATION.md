# F139 V19 — original SQLite atomic pre-request reservation, without POST

**Status: DRAFT source qualification only.** Parent exact-qualified [#1043](https://github.com/spoonman136668-ai/FORGE/pull/1043), source `22b258bac1b0b4ec5940899bc0572d61ea19ea2b`. This gate intentionally has **no controller entrypoint, provider transport, GitHub writer, credentials, automatic lane selector, model publication, release deployment or scientific acceptance.**

## Added genuine original-ledger write path

The isolated `reserve_original_intent_without_post` function writes directly to the existing **original** F139 SHA-linked `Database.events` via `Database.event("NATIVE_RENEWAL_ATTEMPTED", ...)` inside **one original SQLite `BEGIN IMMEDIATE` transaction**. It does **not** write to #1042's disposable simulated SQLite.

The function is deliberately **disconnected** from the original F139 300-second run loop and any external model route. The running deployed original owner cannot invoke it unless a separate protected release explicitly integrates it. Its returned report always says `original_owner_request_authorized=false`, `provider_requests=0`, `paid_model_calls=0`, `worker_dispatched=false`, `scientific_first_use=false`.

### Reservation requirements

1. The **actual original `Database`** object, existing `SingleOwner` lock held on its canonical sidecar path and a caller-supplied original owner witness must all attest, both before and inside the original write transaction. Invalid/disabled/legacy-unsuspended owner or READY/ACTIVE work is denied. No second controller or alternate SQLite.
2. Re-run `Database.verify()` under the `BEGIN IMMEDIATE` original transaction, validating historic hash-chain, native task admission, verified terminal and old negative custody, including new [#1043](https://github.com/spoonman136668-ai/FORGE/pull/1043) cold V19 event checks.
3. Derive the newest real native terminal ticket, lane, target commit, native path, terminal event SHA, evidence SHA and immutable V19 scope from the **original** ledger—not caller-submitted claims. Bind original FORGE active source SHA, prior event head and hash of historical free/model publication event identities.
4. Count **historical spent V17/V18 `FREE_REASONER_ATTEMPTED` and all V19 attempts** together for max 2 per UTC day, 1 per lane/day, 40 total per rolling 30 days and 20 per lane per rolling 30 days. Preserve V17/V18's distinct original 8-request lifetime limit unmodified. An unresolved original model publication, a consumed terminal, or a day rollback must not create a new request.
5. Append exactly one original `NATIVE_RENEWAL_ATTEMPTED` event with `request_intent_committed=true`, `retry_allowed=false`, paid calls=0, worker-dispatched=false and scientific first-use=false. **Cold-verify the entire original history before COMMIT.** Failure at any stage atomically rolls back both original events and `meta.head_seq/head_hash`.
6. A committed event stays spent on cold restart, a lost response or a new UTC day. A source change does not redeem the same native terminal. **A completed reservation is NOT authority to call a provider.** This module contains no POST function.

### Qualification and no-regression

Tests in `f139/test_nci04_v19_original_atomic_reserve_no_post.py` create genuine original SQLite and native terminal fixtures. They exercise valid original append/cold reopen, duplicate/next-day no replay, crash-like rollback after append before COMMIT, lost post-commit receipt, old free budget and terminal-watermark denial, missing native evidence, disabled owner, absent mutex/owner witness, source/head tampering, malformed lane/day and no network/model/GitHub calls.

Require exact-commit full F139 native Python qualification on Windows and Linux, full public repo Linux and Windows qualification and F139-D Windows+Linux hosted development rehearsal before accepting this draft. No original task, live owner file, GitHub accepted ref, branch protection, paid model service or real model proposal is modified. Restore the PR base to qualified parent after main-targeted CI.

## Separate operational and scientific gates, explicitly NOT granted

- V18 actual protected release and original-owner guarded cutover. Repository administrator release protection is now installed, but this does not authorize a V18 merge, source transition or source ref change.
- A distinct **original-only** post-reservation transport release must validate independently public source and bounded prompt, authenticate a genuinely free endpoint and prohibit retries/fallback, source drift and ambiguous publication. No foreign model can sign or approve native results.
- Later real natural, repeated Wingless and Yggdrasil terminal→request→proposal→isolated qualification→next original decision feedback, plus controls demonstrating learning/retention/transfer and retail CPU/RAM use. A dry run and an original ledger event alone are **not** proof of model self-improvement.

**Safety boundary:** no new orchestration scheduler/queue/controller; no CKB-plane dependency; no live original Windows source or original-owner database access during qualification. Keep draft until a separately scoped, qualified and explicitly authorized release gate.
