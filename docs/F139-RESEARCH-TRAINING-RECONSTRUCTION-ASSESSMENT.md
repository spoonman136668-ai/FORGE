# F139 bounded reconstruction assessment: research ↔ training steering

**Status:** developer-only phase-routing preview, not live control, 2026-11-18. Preserve the original F139 SingleOwner, its mutex, source-pinned policy issue #807, SQLite ledger, signed worker receipts, scientific authority, all negative outcomes, native checkpoint ownership and independent Wingless/Yggdrasil/TTT-Hybrid lanes.

## Verified current-state facts (protected FORGE main `c06403c8b6035c6c7013866a7ea08cef1244b507`)

- `f139/local_controller.py` contains the original owner's idle work intake, candidate ranking, issue publication and model-free fallback. No second controller is necessary.
- `f139/nci04_autonomy_feed.py:prepare_feed` authenticates owner PR development candidates and offers source-pinned advisory ordering; policy #807 currently disallows scientific first-use.
- `f139/nci04_research_steering.py` verifies immutable research steering documents and fair lane order, but it has no training-mode contract.
- `f139/nci04_model_free_search.py` has three finite source operators, then the already-defined GenEnv fallback; it is not an open-ended mechanism generator or native training loop.
- Live original-owner read-only run `44428703404` proved running source, ledger integrity and terminal custody but observed repeated `MODEL_FREE_SEARCH_BLOCKED_FAIL_CLOSED`, zero authenticated development candidates. The classified `failure_code` is not exposed by its current read-only status projection. This is **not** evidence of continual autonomous science.
- FORGE CKAD developer PR #1808 and Yggdrasil checkpoint evidence are not authorizations for actual first-use or promoted training.

## New steering contract — intent versus authority

At an existing owner-controlled **new-work intake boundary** only, choose a requested `AUTO | RESEARCH | TRAIN | HOLD` mode, optionally scoped to one independent lane. `HOLD` means stop admitting *new* work, not cancel/abandon existing tasks or training. User-selected modes must be authenticated, recorded with source/epoch/custody and supersedable through the same existing owner policy; no new scheduler, queue, competing consumer, chat-as-authority or new recurring task.

1. **RESEARCH:** choose independently authenticated development hypotheses, causal experiments and native integration opportunities. Absence of eligible research is an explicit idle reason, not an automatic override of manual choice.
2. **TRAIN:** choose a source-owner-verified continuation of the exact native checkpoint and frozen training protocol, preserving cumulative weights, learned state, negative history and cold restoration. Routing alone **cannot** confer a training permit, first-use, budget, protected evaluation, promotion or ref update.
3. **AUTO:** alternate prospectively based on qualified readiness, verified learning progress and negative evidence. When two consecutive authentic *scientific* training evaluations show no gain/regression, prefer research rather than repeatedly train the same unsuccessful method. Never derive improvement from engineering CI or invented metrics. Require independent strong controls, retention, transfer and whole-process cost.
4. **HOLD:** do not admit new work, preserve and reconcile in-flight work, and continue read-only health observation. No interruption, rollback, replay or new owner process.

Manual lane selection cannot silently redirect to another lane. Cross-lane fairness uses only genuine original-owner admissions. Unauthenticated or exhausted candidate sources are **IDLE / NEEDS SOURCE**, whereas transport or custody errors are **BLOCKED / NEEDS REPAIR**. A failed scientific experiment is a retained negative, not a retry authorization.

## Implementation seam and limits

`f139/nci04_phase_steering.py` is a **pure, read-only reference decision function**. It accepts only externally prepared lane-readiness sets and historical outcome summaries; neither the values nor the returned selection are source-authenticated by this module. It makes no API calls, runtime mutations or dispatches. `f139/test_nci04_phase_steering.py` covers manual/auto/hold, lane isolation, fairness, poor training progress, invalid input and authority-negative assertions. This proposal does **not** wire it to F139 and does **not** change the installed owner.

## Bounded reconstruction path

1. **Identify actual idle blocker:** qualify a safe read-only projection of the already-allowlisted model-free `failure_code`, and distinguish genuine finite-source exhaustion from GitHub failure, history exhaustion, task drift or source mismatch. Retain G145 protected-workflow guards; do not merge draft #1817 without separate admission.
2. **Source-bound operator steering:** implement and test an authenticated, epoch/source-bound selection on existing F139 intake, with replay-resistant audit history, manual mode handling, and no mutation of in-flight work. The preview is not the permit system.
3. **Real training adapter:** connect to each independent learner's qualified original source and checkpoint, continuity/retention evidence, budget and authorized scientific first-use. Preserve strong controls and cold restoration. Do not train from a source-only development PR or held-out negative.
4. **Failure and recovery proof:** original-owner exclusive execution, idempotent planning, no uncertain-effect replay, crash/cold restore, mode flip during in-flight task, no candidates, unavailable evaluator, source drift, three-lane fairness, and manual HOLD under active work.
5. **Exact-source qualification and measured autonomy:** focused/negative/interface tests; mandatory final full Linux/Windows regression and build; separately authorized live-owner acceptance with real research→training→evaluate→research progression, persisted native state and measured time/cost. Engineering PASS is not scientific improvement.

**Architecture decision:** reconstruct the owner-facing intake/selection seam incrementally, *not* wipe databases/checkpoints, restart independent research, copy CKB-plane, or replace the original F139 owner. Nothing here authorizes deployment or original scientific first-use.
