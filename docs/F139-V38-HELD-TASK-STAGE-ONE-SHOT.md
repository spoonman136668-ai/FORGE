# FORGE F139 V38 — staged original held task diagnosis, source-only route

## Authority and isolation

The operator issued standing authorization for FORGE work on 2026-11-14,
including further *bounded* read-only diagnosis. This does not remove original
Windows owner, G145, single-owner, task-state, scientific-first-use, cold custody
or controlled-promotion fences. No new scheduler, queue, controller, task or
consumer is introduced; the only registered job is one original-owner
issue-comment read-only check, serial with the existing V41 owner group.

Prior original-host evidence is:
- [V38 first read-only preflight run #43658624013](https://github.com/spoonman136668-ai/FORGE/actions/runs/43658624013): first attempt FAIL at held task identity
- [Bounded followup run #43660563209](https://github.com/spoonman136668-ai/FORGE/actions/runs/43660563209): first attempt FAIL with `F139_V38_HELD_TASK_GUARD=UNCLASSIFIED`
- Latest main parent `396a1a36aec66a47d798ac677bf3ed473c3fa27f`; tree `b59a9644b32a11ea5aafea004a54f2f6919d59dd`
- Frozen original task guard SHA `9bda78341bc3651e8b7b0a24ea6c7858dbff05c6`.
- Original issue #807: two lanes Wingless/Yggdrasil, `scientific_first_use=false`, no task/queue/scheduler changes.

## Exact diagnostic

New one-shot issue #807 owner comment **only after** merge and postmerge full
protected-main qualification:

```text
F139-V38-HELD-TASK-STAGE-DIAG <new-main-sha> 6886931814
```

Registered workflow `.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml`
uses `issue_comment: created` only, `FORGE-CODEX-REMOTE` original Windows
runner, exact source SHA and original guard SHA, no schedule, no push dispatch,
no GitHub write permissions, no task mutation, no original SQLite open.

The stage-specific output is exactly one of:
- `AUTH_INVARIANT` or `AUTH_PROVIDER`: new owner authorization, prior failure provenance, policy, or read-only GitHub GET did not qualify
- `TASK_PREREQUISITE`: original path/PowerShell environment precheck failed; no task guard subprocess was run
- `EXIT_41` through `EXIT_51`: the **unchanged original** PowerShell task guard was executed once and returned that bounded code
- `SHELL_TIMEOUT` / `SHELL_UNEXPECTED`: task probe or PowerShell returned an unexpected status, with no raw command/path/SID disclosed
- `TASK_UNEXPECTED` / `UNCLASSIFIED`: no reliable bounded condition established
- `POSTCHECK_DENIED`: protected main drifted or final provider read failed
- `PASS_PREDICATES_ONLY`: original guard alone passed; **not** complete cold ledger acceptance

PowerShell/SQLite contents, SID, paths, tokens, stdout/stderr and exception
messages are not printed. The script calls the old `profile.readback` only
once and never changes `profile.py`. Authentication uses first-attempt
owner issue intent, original failed run, previous comment, and read-only
protected-main/issue policy.

## Exact source qualification and stop rules

New PR with **exact seven paths**: this document; the new one-shot workflow;
the source/test module `f139/nci04_v38_held_task_stage_diagnostic.py` and
`f139/test_nci04_v38_held_task_stage_diagnostic.py`; and unchanged-purpose
`scripts/check_rar_g145_pr_scope.py`,
`scripts/check_rar_g148_go_cache.py`,
`scripts/check_rar_g156_dynamic_base_cache.py`. G145 pins owner PR,
frozen predecessor SHA/tree, source inventory, exact new workflow blob, and
the original task guard. Generic workflow or CI harness edits remain denied.

Require all 12 exact-candidate first-attempt Linux/Windows/native/development
jobs PASS, exact-tree merge on protected main, and 8/8 first-attempt full
postmerge main regression. Only then may a **fresh** owner-authored comment
trigger one diagnostic attempt. Never replay the prior two failed runs or
repeat a lost-acknowledgement run. No status code authorizes the source event
#1831, three-lane policy, owner restart, task edit or scientific first-use.
