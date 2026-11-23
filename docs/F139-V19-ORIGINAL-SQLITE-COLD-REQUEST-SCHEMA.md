# FORGE F139 V19 — original SQLite cold request-intent schema (verify-only)

**Status: source-only draft; NO original owner release or remote model request.** Parent: [#1042](https://github.com/spoonman136668-ai/FORGE/pull/1042), exact `364b076d60298c009b5c3344638880085b4013d7`. This gate adds one small check to the **existing** `Database.verify()` and no call from the existing `run_once`, original Windows scheduled task, free-provider path or worker runtime. The live V17 source and its original SQLite remain untouched. No new controller, scheduler or queue.

## Specific advance beyond memory-only rehearsal

A planned production research attempt must eventually be durable in **the actual original SQLite SHA-linked event chain** before any external request. The previous #1042 used anonymous `:memory:` SQLite to prove atomicity but could not show that original `Database.verify()` would even recognize the proposed attempt event.

This gate defines `NATIVE_RENEWAL_ATTEMPTED` with exact schema `forge.f139.v19.original-request-attempt.v1`. A record binds the *actual* original event prior head, F139 source SHA active at the request, original native admission ticket, terminal event sequence and event SHA, lane, original terminal evidence SHA, target commit/path, immutable V19 scope, SHA of all prior original free/model-draft event identities, UTC day, and hardcoded no-retry/no-paid/no-dispatch/no-science claims.

The single new verification hook runs at the **end** of original `Database.verify()`, after the unmodified historic SHA chain, original native task evidence, negative custody and original source-transition audits. It independently scans events in sequence and rejects:
- missing or chronologically invalid original native admission→verified terminal→attempt ancestry, lane/commit/path mismatch, replay or older/equal terminal;
- changed release source, fake terminal digest, invalid attempt fields, wrong original prior-head binding, altered original free/draft history seal;
- unanswered original model draft publication attempts, duplicate previous intent, wrong or rollback UTC day, inappropriate per-lane/total 1-day or rolling 30-day budgets including **spent historic free attempts**;
- retry, paid API, worker dispatch, or scientific first-use claims.

The audit is a **read-only cold verifier**. It has no model token, transport, provider request, original-owner POST, production append function, source promotion or activation permission. Historic V17/V18 event semantics and 8-request lifetime budget are untouched, and the no-V19-event branch preserves all existing behavior.

## Isolated original SQLite acceptance

The separate regression uses the real existing `Database`, `SingleOwner` and native issue-admission/terminal fixture. It appends a synthetic intent under original `db.transaction()` to **disposable local test SQLite only**, cold-reopens with the regular `Database` and verifies that a matching genuine native terminal is accepted. Malformed, unauthorized, replayed, source-drifted or budget-escaping intents must be rejected with automatic transaction rollback. The test neither calls an external provider nor touches any live original Windows artifacts. The source helper itself never inserts.

Required qualification: exact-HEAD F139 Windows/Linux source tests, full public Windows/Linux regression, and F139-D hosted development rehearsal. Keep draft on #1042 after the main-targeted checks finish.

## Remaining hard blockers to operational V19

- An independent administrator must establish the exact immutable `f139-owner-release-*` GitHub branch rule; only the protected main rule is active today. V18 combined source [#1039](https://github.com/spoonman136668-ai/FORGE/pull/1039) remains qualified but undeployed. No backdoor source promotion, task modification or issue #807 cutover.
- A separately qualified V19 release must implement original-owner **read–validate–append reservation inside `BEGIN IMMEDIATE`** under the *existing* `SingleOwner`, with a cold original Windows exact-SHA source release. The writer must reserve exactly one original append-only attempt before any free request, prohibit retries after ambiguity, and preserve every earlier original event. The verification code alone deliberately cannot request.
- The active model-generating worker, actual bounded free inference and two-lane natural terminal→proposal→independent qualification→next decision cycle, with credible retention/transfer and resource controls, remain future proof obligations.

**NO GO** for deploying production V19, merged-source science authority, free/paid API calls or accepted model ref mutations. This gate changes source verification semantics only in its review branch.
