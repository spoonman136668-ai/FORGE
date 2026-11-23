# F139 V19 — atomic free research-request reservation REHEARSAL (inert)

**Status: DRAFT, unmerged, source-only laboratory.** Parent is [FORGE #1041](https://github.com/spoonman136668-ai/FORGE/pull/1041) at `43f35df06b0f5427c1b1dc956073e5ef80e43efa`. The live Windows F139 V17 original SQLite, scheduled task, source, existing finite free lifetime cap and historical event grammar are unchanged. The V18 administrator-only immutable release-ref prerequisite remains unsatisfied. No model, provider, remote GitHub, research-experiment or scientific authority is granted by this rehearsal.

## What this gate qualifies

An at-most-once **hypothetical** free-request reservation requires both earlier V19 trust gates:
- [#1040](https://github.com/spoonman136668-ai/FORGE/pull/1040): an actual `NATIVE_DEVELOPMENT_ADMITTED` and `PROVIDER_VERIFIED_TERMINAL` in the already verified original SQLite chain, exact lane/source/manifest and **newer than prior original free/draft attempts**; held original `SingleOwner`, enabled and quiescent.
- [#1041](https://github.com/spoonman136668-ai/FORGE/pull/1041): all original `FREE_REASONER_ATTEMPTED`, `MODEL_DRAFT_ATTEMPTED`, `MODEL_DRAFT_AUTHENTICATED` are cold verified. An ambiguous model publication blocks; spent free requests count against budgets and cannot replay after failure, source revision or clock rollover.

The new `f139/nci04_v19_atomic_reservation_rehearsal.py` creates an anonymous `:memory:` SQLite **simulation log** with an exact internal schema, explicit `BEGIN IMMEDIATE`, uniqueness of terminal ticket and scope, append-only update/delete guards, SHA-256 event-link verification and durable-within-transaction rollback. It first rejects anything but that anonymous memory log; it refuses the **actual** original-owner connection and any disk-backed or attached SQLite file before starting a transaction. The original database is read-only and cold verified before/after. It combines old free attempts and simulated V19 attempts under max 2 total/UTC day, 1/lane/day, 40/rolling 30 days, 20/lane/rolling 30 days. All historical failed or ambiguous original attempts remain spent. No date rollover can buy the same terminal again.

If and only if the simulated chain, original event head and fresh native terminal all qualify, the code inserts one **simulated** event with the terminal identity, immutable scope, historical original head, legacy-history hash and prior rehearsal event hash in one transaction. Fault injection rolls back before commit; a second attempt to spend the same terminal is blocked even on another day. This is not a real pre-POST reservation and cannot perform a POST.

Every returned record, including a successful in-memory rehearsal, states `original_owner_request_authorized=false`, `real_original_ledger_events_written=0`, `provider_requests=0`, `paid_model_calls=0`, `worker_dispatched=false`, `scientific_first_use=false`, `accepted_ref_mutations=0`.

## Independent qualification

`f139/test_nci04_v19_atomic_reservation_rehearsal.py` runs against the existing genuine isolated original SQLite fixture, not the live original owner. It tests fresh-terminal one-time reservation, repeated same-terminal/no-replay after UTC rollover, transaction rollback on injected pre-commit failure, original-byte and event-head invariance, append-only triggers, locked-owner requirement, persistent/original DB refusal, absent or inflight native history, no remote transport and owner event-chain tampering. Full standard F139 + Linux/Windows regressions and the actual F139-D hosted rehearsal must pass on one exact SHA before accepting this source-only gate.

## Explicit additional conditions before real V19 activation

1. **Finish and verify V18 source promotion and protected release branch enforcement.** A draft and a passing CI run are not an administrator-installed ruleset or original-owner source cutover.
2. Original-owner V19 source transition must pre-register an append-only **production** `V19_*_ATTEMPTED` schema and cold DB verifier, preserving every old event and former free/draft attempt. Production `Database.verify()` must reject forged/duplicate/cross-lane events, not reinterpret old history, and still validate V17/V18 negative custody.
3. Replace the anonymous rehearsal log with **one atomic append on the existing original SQLite** under existing `SingleOwner`, with event chain, fresh-source and evidence revalidation inside `BEGIN IMMEDIATE` **before** one free provider POST. No ambiguous POST retry, ever; every attempted request consumes its scope.
4. Prove real free-only model path, no paid fallback, exact source and public data verification, bounded model proposal, independent deterministic Linux/Windows tests, worker isolation, and FSA authority. The controller must never merge model-generated code or accept scientific results on a model assertion alone.
5. Demonstrate several **naturally scheduled** Wingless and Yggdrasil feedback→proposal→qualification→next-decision cycles (including negative result and repair cases), with matched conventional controls, resource accounting, learning, retention and transfer. These shadow tests are **not** scientific progress or autonomy proof.

No new controller, queue or scheduler; do not use CKB-plane as routine control authority. This draft must remain unmerged pending exact source qualification and a separate safe release plan.
