# F139-A — Unified FORGE controller with GitHub-hosted execution-only workers

**Status:** Inert source implementation; NOT deployed, activated or entrusted with scientific first-use. Existing F136/F137 orchestration remains authoritative during qualification. This is not a claim of live autonomous research or Cloudflare deployment.

## Reuse what exists

FORGE already has qualified synthetic workers, `cyclecontroller/`, `workerreconcile/`, `durableauthority/`, existing F136/F137 source guards and GitHub Actions infrastructure. These are left unchanged. F139 replaces competing orchestration decisions only after a separately authorized cutover, not by adding another permanent controller.

`f139/core.mjs` is the single controller decision kernel. `f139/cloudflare.mjs` is an initially inactive Cloudflare Worker runtime with an existing-D1-compatible persistence adapter and a GitHub Actions REST execution adapter. `f139/d1.sql` creates a standalone FORGE-only monotonic CAS record, append-only event journal, fixed-purpose queue and once-only completion records; it initially seeds **no tasks**. No Cloudflare cron, D1 production migration, public control HTTP endpoint, deployment credentials or paid model service is introduced.

## Exact execution contract

Only previously reviewed **development-only** tickets in Wingless, Yggdrasil or Qualification can be selected. Each ticket is pinned to the exact protected FORGE `main` source SHA and monotonic owner epoch; arbitrary commands, arbitrary workflow targets, unbounded queues and scientific originals are rejected.

The **single controller**, not GitHub, chooses a ready ticket, commits `START_RISK` with its unique identity and daily budget (max 48 new starts/day), signs the ticket via an HMAC key shared with the worker, and POSTs once to the dedicated `forge-f139-development-worker.yml` GitHub workflow. The workflow has **only** a `workflow_dispatch` event: no `schedule`, `push`, `workflow_run`, or PR-based autonomous dispatch. Its native Ubuntu/Windows runners check the signature, exact source/event identity, and original attempt before executing FORGE's existing synthetic model-free development command and uploading their source-bound receipts.

The controller independently discovers a uniquely named workflow run from GitHub, verifies exact event, main branch SHA, first attempt, successful native OS jobs and unexpired GitHub artifact hashes. It records **provider-verified development metadata** and source-bound terminal custody; this is NOT an issuer-signed original science receipt or permanent original ZIP archive. It writes completion before advancing the next approved ticket automatically; GitHub workflows never decide what to run next.

### Crash, recovery, and safeguards

- A durable start-risk intent precedes external POST. On timeout, interrupted POST or process crash, the same ticket is **never blindly dispatched again**. Subsequent controller ticks perform read-only provider reconciliation. Missing or ambiguous evidence remains pending/quarantined, not reinterpreted as no work.
- One D1 compare-and-swap controller authority row serializes version/epoch transitions. A SQLite trigger stores each winning transition into an immutable event journal in the same transaction. Missing, modified or conflicting evidence must fail closed.
- An append-only completion table rejects conflicting run IDs and avoids replay after restart. At most one new ticket may dispatch per controller tick; an authenticated terminal may lead directly to the next eligible task.
- Daily quotas, source pins, fixed existing lane names, strict HMAC ticket identity, source-ledger hashes, exact first-attempt GitHub source and OS evidence checks remain mandatory.
- Scientific original dispatch, sealed confirmation first use, optimizer promotion, accepted refs, real broker access, paid AI APIs and Codex remain denied. FORGE never depends on CKB-plane. The separate Wingless and Yggdrasil scientific authorities remain intact.

## Activation prerequisites — NOT performed by this PR

1. Verify F139-A PR source identity, run adversarial Node, Python, and SQLite tests natively on Ubuntu and Windows plus complete repository regression. Review exact GitHub branch protection before authorizing a merge.
2. Check the existing Cloudflare Worker/D1 account, exact D1 database binding, backup/time-travel recovery and relevant cost ceilings. **Never apply the migration blindly to a production first-use database.** Qualify the GitHub App installation token, minimum repository Actions permissions, short token lifetime, and separate worker HMAC secret. No password or paid service should be copied into Git.
3. Deploy a **disabled shadow instance** (`F139_ACTIVE` unset; no cron or seeded tickets) under an independently qualified owner epoch. Test D1 restart, source drift, interrupted dispatch, lease/epoch CAS, duplicate suppression and exact evidence retention. Seed only two synthetic reviewed development tickets for real hosted-runner acceptance. Retain every negative.
4. Freeze the successor source and verify the old F136/F137 development dispatch mechanisms have actually been disabled. Under separate cutover authorization, attest `F139_LEGACY_SUSPENDED=true`, activate `F139_ACTIVE=true` and enable exactly one Cloudflare-owned schedule. **Never run F139 alongside active legacy dispatch owners.**
5. Demonstrate two consecutive source-qualified, genuinely unattended development tickets with automatic post-verification succession. Then extend adapter coverage to existing research/optimizer worker types only after their own independent scientific authority, original-risk and budget qualifications.

The immediate next gate after F139-A qualification is **F139-B authentic hosted-execution and persistent Cloudflare/D1 cutover rehearsal**, not more GitHub-to-GitHub controller chains. F138-C2 PR #533's read-only relay-classification problem stays independently tracked; F139 does not retroactively mark it green.
