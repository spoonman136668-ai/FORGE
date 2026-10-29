# F139 V19 — Original V18-to-V19 source-transition engine

**Scope: SOURCE-ONLY, DRAFT, NOT DEPLOYED.** This gate adds the missing `forge.f139.source-transition.v19` cold-verifiable original SQLite event schema, and extends the existing atomic `Database.transition_source(..., allow_v19=True)` engine. V19 admission is **off by default** and is not wired into the original `cli()`, its scheduled Windows task, existing release workflow, or any live model-transport/publishing loop. It is not cutover authorization.

## New, one-time custody checks

An exact V18 original ledger is required: the prior transition chain must end in one V18 event with original source `d8bccc604f8607bf10f9d8bc6aa568d1f98af559`, native activation must remain authentic, the existing `SingleOwner` mutex must already be held, original owner enabled and legacy dispatcher suspended, no pending READY or active tickets, complete known negative-custody tickets and provider failures, and the proposed V19 SHA must never have appeared in transition ancestry.

The *existing* SQLite `BEGIN IMMEDIATE` transaction snapshots verified/quarantined tasks, original G3/model/free-attempt history, provider-failure identity and the exact immutable V18 terminal-event SHA. It updates only the original metadata source and appends exactly one source-transition event in the same transaction. Original `Database.verify()` cold-checks schema fields, V18 predecessor, negative receipts, model history, immutable task fingerprints, no repeated V19 transition, `new_dispatches=0`, `scientific_first_use=false` and `v2_receipt_authorized=false`. A failure rolls back the attempted source update and appended event.

## Safety and next gate

The new isolated regression uses **synthetic fixture history** and patches original historical custody checks explicitly; it tests the actual transactional branch, mutex, off-by-default flag, exact V18 predecessor seal, duplicate refusal, pending task denial and post-event rollback. It does **not** pretend its synthetic ledger equals the live original Windows SQLite. Full native Linux/Windows, public and hosted CI are required for any source-qualification claim.

The original Windows CLI intentionally has **no V19 transition command yet**. A later separately qualified owner release workflow must authenticate real Windows principal/SID, original task/trigger/action, original cold SQLite event head, source-ref protection, installed clean release, independently cold-verified backup/rollback, owner GitHub identity and a controlled stop/resume. Only that gate may expose a one-time explicit command and update the policy #807 source pin. Do not merge to protected main, mutate the original task or SQLite, contact a real model provider, create a second controller, consume paid API, publish native PRs or accept scientific first use from this gate alone.
