# F139 H53 original-owner one-shot audit — inactive contract

Status: PREPARATION ONLY. This document is not a GitHub Actions workflow and cannot trigger execution.

## Qualified input
- Observer qualification commit: `f89b8e08cafa1fbf2dc5584c00e3b87fea77ddee`
- Original installed V26 source: `49c7b15343bea3c201fb52b498d8c0f397384afe`
- Historical H52 baseline: event sequence 350, SHA-256 `17614edebb1b067de8112615637160e2bd7e71a4b3ac05dbab78fc360eba3d97`.
- Exact-head focused Linux/Windows: run 41249207523 PASS.
- Exact-head development rehearsal Linux/Windows: run 41249207529 PASS.
- Exact-head public Linux/Windows: run 41249207484 PASS.
- Exact-head F139 native Linux/Windows: run 41249207427 PASS.
- These receipts apply to the qualified observer source only; any change to that source or its relevant interfaces requires fresh qualification.

## One-shot release requirements (fail closed)
1. A separately approved, uniquely named H53 audit branch must be created exactly once from the deployed V26 commit. The branch must contain only the reviewed one-shot workflow and strictly pinned observer bytes. Do not reuse the H52 audit branch, workflow name, or owner approval token.
2. The audit branch must be protected by one active exact-ref branch ruleset prohibiting update and deletion, with no bypass actors. Verify ruleset readback immediately before the audit.
3. Require a single exact owner-authored approval on the existing authorized owner approval channel, binding the **final audit commit SHA**. No historical approval or chat instruction substitutes for that approval.
4. The workflow must accept only the first non-forced branch-creation push, from the authenticated repository owner, on the exact audit ref; refuse reruns and any source or workflow identity drift.
5. Run only on `FORGE-CODEX-REMOTE` with labels `[self-hosted, Windows, forge-codex-isolated]`. Verify original task name, principal SID, enabled/running state, topology, installed clean V26 checkout, and original database path.
6. Invoke the pinned H53 observer with the original database opened in SQLite `mode=ro` and `query_only=ON`. Perform independent `f139.local_controller.Database.open_readonly(...).verify()` using original V26 code; never invoke the controller or any dispatch.
7. Emit a bounded JSON receipt with audit ref/SHA, installed source SHA, owner identity, event head, baseline hash, scheduler observations, read-only verification, and a conservative unattended-cycle verdict. New ledger events alone do **not** establish unattended reasoning.
8. Prohibit database writes, owner-task changes, branch mutation, secrets, API POST, dispatch, release/promotion, and scientific first-use. The workflow must be `permissions: {}` and have a non-cancelling unique concurrency group.
9. A static guard test must reject wrong ref, missing/duplicate approval, wrong owner, wrong runner, source drift, mutable ruleset, rerun, non-creation push, and any mutation or dispatch action.
10. Run focused static guard tests and affected interfaces on Linux/Windows, then mandatory final regression on the **final audit source identity**. Reuse prior results only for matching immutable content and qualification provenance.

## Current boundary
The existing H53 PR contains the historical H52 one-shot workflow inherited from its qualification ancestor. This is **not** an H53 trigger and must be removed from the eventual H53 integration diff, or the H53 source must be isolated on a clean V26-rooted branch, before approval or promotion. Do not create a competing controller, scheduler, or owner workflow.
