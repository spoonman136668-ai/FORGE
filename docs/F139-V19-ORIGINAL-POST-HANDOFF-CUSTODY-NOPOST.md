# F139 V19 — original one-time public/free-model transport handoff custody (NO POST)

**Status: independent source-only draft; no deployment, credentials or live requests.**
Parent: [V19 original atomic intent #1044](https://github.com/spoonman136668-ai/FORGE/pull/1044) exact `b23ce730dbcde4571091f65bfd03dd5131ded17c`.

## Distinct problem now addressed

A single original `NATIVE_RENEWAL_ATTEMPTED` committed before provider contact in #1044 is necessary, but **not sufficient**, to prevent accidental repeat POST from a later worker interpreting the already-committed reservation as available again. Need separately consumable, single-use provider handoff tied to a specific public request and exact original event, not an informal Boolean or a memory-only counter.

This gate introduces `NATIVE_RENEWAL_POST_ATTEMPTED` with exact schema `forge.f139.v19.original-free-model-post-handoff.v1`. This is a **pre-transport handoff attempt**, not evidence that any HTTP POST happened. Under the held original `SingleOwner` mutex, original `Database.transaction()` starts `BEGIN IMMEDIATE`; after cold `Database.verify()` the writer requires:
- the **immediately preceding** original event to be exactly one cold-verified `NATIVE_RENEWAL_ATTEMPTED` at the supplied original sequence and SHA; any interleaved original event or previously spent handoff refuses a second send, including after cold reopen/UTC rollover;
- original owner enabled, legacy suspended, no pending native work, still exact source SHA and lane/native target/path, same UTC day, genuine retained native learning evidence and the previously consumed original free/model budget;
- an exact bounded **public-source-only** proposal packet using the already existing fixed model `nvidia/nemotron-3-ultra-550b-a55b:free`, verified independently from anonymous public Git tree and file bytes; no private original ledger, issue or Mind-Palace notes are transmitted;
- an immutable SHA256 of request body and of public packet, source and history identities, plus original reservation SHA, ticket and V19 scope, with all no-retry/no-paid/no-authorization/no-science flags fixed.

The writer appends ONE new original hash-chain event, invokes the **existing cold `Database.verify()`** before COMMIT and rolls back on any owner loss or injected failure. The cold verifier independently rejects spoofed, duplicated, moved, replayed or nonadjacent handoff records and refuses paid/retry/worker/science authority. All original legacy V17/V18 history and native validation stay unchanged.

## Deliberate NO-POST safety boundary

The function is `custody_original_post_handoff_without_post`, and **does not import, invoke or authorize `infer_free_once`** or any HTTP/GitHub write. The normal F139 `run_once`, 300-second tick, original Windows scheduled task, V17/V18 provider and controller are untouched. The only original-SQLite event writes in this PR are against isolated disposable test databases. On any successful custody result, `provider_requests=0`, `original_owner_request_authorized=false`, `paid_model_calls=0`, `worker_dispatched=false`, `publication_authorized=false`, `scientific_first_use=false`, and `accepted_ref_mutations=0`.

The new tests additionally *simulate* one existing free provider request entirely offline using **explicit injected Python mock transport** with a fake sentinel credential and an anonymous Git source fixture. That response remains untrusted, passes through the existing conservative proposal validator, and cannot write or publish a real candidate. A mocked timeout is permanently spent: cold original SQLite refuses another handoff with that receipt. The mock path and dummy token exist only in tests, never in the new implementation.

## Must pass before any merge or operational claim

Exact-HEAD F139 Linux+Windows source tests (including original cold reopen, request ancestry, public private-source rejection, injected rollback, no request replay, fake timeout, one bounded fake model response); full Go+Python Linux+Windows; hosted F139-D Windows+Linux. Keep **DRAFT stacked on #1044**. No GitHub main/accepted ref mutation, model provider call, paid model, CKB-plane control or FSA authority.

## Remaining real V19 activation gates

1. Independently qualified V18 original-owner release/cutover using its already installed no-bypass immutable release-ref ruleset, final exact-main protected SHA, real owner cold quiescence and single original source transition. The separate V18 workstream handles this; do not race it.
2. Bind a **future separately verified live V19 transport function** to one already-committed original handoff under the same original owner, exact public Git source and single free-only model. An ambiguous POST must consume the handoff forever, with no retry, including crashes. Do not activate from this draft.
3. Bind the source/authenticated model draft writer and independent source controls to the untrusted validated candidate; no worker, GitHub write, merge or scientific first-use by the external model itself.
4. Show repeated naturally scheduled Wingless and Yggdrasil native development cycles with real training evidence, retention, unfamiliar-environment transfer and matched scientific controls, including computational resource accounting suitable for retail hardware.

The true architecture remains original SingleOwner, original SQLite and the existing controller. No alternative ledger, controller or queue is introduced.
