# F139 V19 — exact original-owner one-shot free-model invocation (source-only)

**DRAFT; not deployed.** Parent: [#1047](https://github.com/spoonman136668-ai/FORGE/pull/1047), exact head `e525cb0e0cdd5faefe183e3985ae03fd96bd1606`. The protected V18 main / original owner promotion is a distinct operating lane. This PR adds one original SQLite SHA-chain event schema, its cold verifier, an explicit one-call adapter, and only fake-provider isolated tests. No changes to original F139 `run_once`, scheduled task, owner credentials, GitHub publication, paid APIs, model weights, original live SQLite, source main, or scientific first-use.

## The missing end-to-end boundary

Previously #1044 committed one `NATIVE_RENEWAL_ATTEMPTED` research intent; #1047 committed an **immediately adjacent** one-time `NATIVE_RENEWAL_POST_ATTEMPTED` authentic public request-body handoff, but neither could call a model. The next hazard is a separate worker reusing a spent handoff to POST again after timeout, crash, UTC day change or owner task replay.

`f139/nci04_v19_original_one_shot_free_send.py` defines original ledger event `NATIVE_RENEWAL_SEND_ATTEMPTED` (`forge.f139.v19.original-one-shot-free-send.v1`) and one `one_original_free_send_source_only` adapter. Under the existing held `SingleOwner`, it:

1. Requires the original SQLite entire cold-valid SHA chain, an exact current-head previously consumed `NATIVE_RENEWAL_POST_ATTEMPTED`, current owner-enabled/quiescent source, original source and terminal ticket, target native commit/path, fixed free Nemotron model, and independently authenticated public Git content.
2. Recomputes exact bounded public packet/body SHA256 and independently reads anonymous public source. No private issue, owner key, DPAPI material, memory text or proprietary native repository file is part of the prompt.
3. Starts one existing original `Database.transaction()` / SQLite `BEGIN IMMEDIATE`, cold rechecks the active original owner, exact source/packet, original chain head and existing `SingleOwner`; appends **exactly one** send-attempt intent to the original SHA chain, cold `db.verify()` after append, checks owner still held, then COMMITS.
4. Only **after COMMIT** invokes the existing `infer_free_once`, fixed model `nvidia/nemotron-3-ultra-550b-a55b:free`, maximum one call, bounded response, zero redirects/retries, no paid fallback. The **transport callback and token must be explicitly supplied**. There is *no implicit HTTP transport*, env-secret discovery or runtime hook. All CI execution uses a fake token and injected transport; the actual provider is never contacted by this gate.
5. A timeout, invalid reply or ambiguous exception consumes the original SHA-linked send event forever; cold restart or a new UTC day cannot retry or even repeat public source fetching from the same handoff. A successful result stays **untrusted**; a separate independent candidate validator, authorizing worker, scientific FSA and publication gate are mandatory. Nothing is self-merged or accepted from a model response.

**Cold verifier:** the existing `Database.verify()` imports `audit_v19_send_events` only after the previous original native, free history, V19 request and handoff audits. It rejects forged event fields/authority, incorrect SHA/terminal/lane/scope/model/packet/body bindings, nonadjacent handoff and duplicate send. The no-V19-event path changes no legacy behavior.

**Boundaries:** A source-review branch may define the adapter but may **not** activate the live Windows owner. The 300-second controller tick still does not import it. There is no automated provider call, no task dispatch, no approved release ref for this draft, and no publication/science authority. Passing this gate qualifies an implementation, not an actual authenticated free model request. The live owner must separately receive a safe, approved, protected exact-SHA V19 cutover and genuine credential/owner custody before the future operational use.

## Qualification

Full native original SQLite and mock-transport regression in Linux+Windows: positive one-shot public free model response, cold-reopen, fake timeouts permanently spent, duplicate original handoff, precommit-fault rollback, packet tamper, absent owner mutex, revoked owner witness, malformed token and no implicit network, and forged duplicate send events. All required F139 native, full public, and hosted development rehearsal workflows must succeed on the exact head on both OSes; leave stacked draft until then.

## What is still needed for autonomous self-improvement

A separately validated **runtime owner activation** must bind this adapter into the authorized natural-tick path (while ensuring the mutex remains held and no other controller is created), prove the provider remains genuinely free under live account credentials and at most one POST per spent handoff, and gate all returned candidate code through isolated build, deterministic native tests, adversarial baseline, source publication and scientific validation. Then prove several observed Wingless and Yggdrasil cycles with genuine learning/retention/novel-world transfer and compute/memory resource accounting. Zero CKB-plane routine dependency; no new controller.
