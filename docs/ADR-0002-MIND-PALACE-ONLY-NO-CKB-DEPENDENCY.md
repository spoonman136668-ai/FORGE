# ADR 0002 — Mind-Palace-only advisory bridge; no CKB-plane dependency

**Status:** Standing operator architecture decision, reaffirmed October 16, 2026. **Supersedes the optional CKB-plane historical-import route in ADR 0001** and any subsequent instructions suggesting FORGE should read private CKB-plane owner runs, controller status, evidence ledgers or credentials to qualify FORGE autonomy. Does not itself authorize deployment or scientific acceptance.

## Decision

FORGE is architecturally independent from CKB-plane. **FORGE must not connect to CKB-plane, and CKB-plane does not need to connect to FORGE.** There is no CKB-plane access/permission task to close for FORGE.

The **sole desired cross-project context mechanism is Mind-Palace**, retrieved directly and read-only as bounded, commit-pinned advisory memory. The context route may inform design choices but **cannot authenticate experiments, approve original first-use, sign owner/witness records, accept/promote research, execute experiments or grant a Cloudflare permit.**

All operational qualification must use **FORGE-native** source custody, admission rules, authority records, original-use guarantees, independent reviews, controller/runner isolation and recovery controls. Existing authorized Cloudflare infrastructure may be used where its actual deployment and recovery gates permit. Independent Wingless/Yggdrasil scientific evidence may be admitted under FORGE-owned controls; it must not be routed through a CKB-plane controller or owner.

Prohibited dependencies include CKB-plane private GitHub Actions runs, CKB-plane repository files, owner-wake history, mailboxes/bridges, first-use ledger and seed/lease records, worker queues, controller/PIDs, witness signatures, credentials and runner access. **Do not propose cross-repository tokens or new CKB-plane permission grants** when FORGE's own evidence is missing. Instead implement the missing FORGE-native capability or honestly retain the FORGE blocker.

Historical references and legacy schemas already frozen in FORGE archives remain as provenance. They are **not** live importer authorization; do not retroactively rewrite or erase accepted records.

## Explicit correction

The earlier attempted F87 [PR #354](https://github.com/spoonman136668-ai/FORGE/pull/354) wrongly made a FORGE-native gate depend on private CKB-plane owner Actions evidence. The PR was closed without merge. Its HTTP 404 was a consequence of the wrong architecture, not a request for operator credentials. That approach must not be revived or generalized.

## Verification question for every FORGE gate

> Would this gate still be scientifically and operationally meaningful if CKB-plane and its API were entirely unavailable, while Mind-Palace remained readable for advisory context?

If no, redesign it before implementation. Passing this test does **not** substitute for genuine FORGE-owner signatures, first-use ledger custody, source-bound artifacts, independent acceptance or safely authorized Cloudflare changes.

See `AGENTS.md` and `spoonman136668-ai/Mind-Palace/docs/FORGE-ISOLATION-BOUNDARY.md`.
