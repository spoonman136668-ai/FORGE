# F139 V38 — original Windows held-task guard diagnostic, one shot

## Explicitly approved, minimal scope

The operator approved **one distinct, bounded, read-only diagnostic** to identify which original task-profile PowerShell exit predicate (41–51) failed in the previous preflight. This is NOT permission to rerun prior issue comment `6886633573` / run `43658624013`, read/write SQLite, repair a task, change its source, start the controller, alter three-lane policy, dispatch science, or create any scheduler.

Protected-main frozen parent `46a97e22ccd061ed799b53a8b92f27ed48b98f2b`; tree `2f6a8766fa8dac77531697e2990169464d600dc8`. Failed preflight first attempt: run `43658624013` returned aggregate `F139_HYBRID_V38_HELD_TASK_SID_SOURCE_OR_QUIESCENCE_NOT_VERIFIED`, after passing owner event and release and before touching original ledger.

Engineering branch `engineering/f139-v38-held-task-guard-diagnostic-once-20261114`. Exact seven changed paths are this document, `f139/nci04_v38_held_task_guard_diagnostic.py`, `f139/test_nci04_v38_held_task_guard_diagnostic.py`, `.github/workflows/f139-v38-held-task-guard-diagnostic-once.yml`, and unchanged-purpose G145/G148/G156 source-scope admission modules. The workflow is immutable-blob constrained in G145, with exact PR owner, issue, base SHA/tree, file inventory, and unchanged V38 original task guard blob.

## Read-only behavior and output

Original Windows `FORGE-CODEX-REMOTE`, exact protected-main checkout, first attempt only; shares original V41 owner workflow concurrency and uses a fresh owner-authored issue #807 comment after qualified merge and first-attempt postmerge main regression:

```text
F139-V38-HELD-TASK-GUARD-DIAG <exact-current-main-sha> 6886633573
```

The diagnostic authenticates both issue comments and the failed run via bounded native GETs; checks original two-lane policy and source; calls the **unchanged** `profile.readback` once. It only returns `F139_V38_HELD_TASK_GUARD=EXIT_41` ... `EXIT_51`, `PASS_PREDICATES_ONLY`, or `UNCLASSIFIED`. No paths, SID, command line, PowerShell errors, SQLite content or raw output are printed. A code is a bounded diagnostic classification, NOT successful original-owner preflight or permission to repair; `UNCLASSIFIED` fails closed.

The exit-code mapping is frozen in the existing production task guard: 41 SID/owner; 42 action/trigger count; 43 executable; 44 argument parser; 45 original database path; 46 wrapper name; 47 root/Python/wrapper existence; 48 allowed original source SHA; 49 checkout cleanliness; 50 task disabled/enabled flags; 51 active matching Python controller process. All guard checks are read-only. A subcode does not prove the other original-host conditions or record any cold ledger proof.

No new schedule, controller, task, queue, workflow_dispatch, paid API or native science changes. Even a **PASS** never authorizes restart, source event #1831, Hybrid schema migration, issue policy update, or worker dispatch.

## Qualification and release

Require 12/12 full original Linux+Windows/native/development exact candidate checks, exact workflow blob and G145 file scope, protected-main merge with identical candidate tree, first-attempt full postmerge main 8/8, then exactly one separate fresh owner comment. Only after that comment may the original Windows runner execute this read-only diagnostic. A failed first attempt is never replayed.
