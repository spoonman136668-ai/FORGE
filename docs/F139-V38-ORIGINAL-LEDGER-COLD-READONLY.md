# F139 V38 original-owner ledger and cold-backup read-only qualification

## State and authority

The original Windows scheduled task was independently inspected at V5:
https://github.com/spoonman136668-ai/FORGE/actions/runs/43703208070
Its result was F0000-U0000: 11 predicates observed PASS and no unknowns.
No task or SQLite mutations occurred. The historical original owner guard
PowerShell 5.1 syntax was corrected in PR #1770 and qualified under Windows
and the first-attempt main regression. This does NOT establish the current
SQLite event chain or independently verified cold backup.

The original policy in issue #807 remains exactly Wingless/Yggdrasil,
scientific_first_use=false, no paid API and no scheduler/controller changes.
Original V37 source event #1830 and predecessor historical 153 verified /
56 quarantined tasks must be preserved. No hybrid scientific first-use,
source commit, schema migration, task start, restore, policy change or
third-lane admission is authorized by a read-only receipt.

## Scoped code and original-owner route

PR #1771 modifies the EXISTING V38 read-only preflight workflow rather
than creating a new controller/scheduler/queue. A distinct workflow concurrency
group avoids unrelated skipped workflow cancellation; inside the owner read,
the original SingleOwner mutex protects the SQLite cold read. This
workflow never calls a task mutation, opens the database writable, or submits
scientific work.

A new owner-comment prefix consumes predecessor V5 comment 6892848524,
whose exact source SHA is 2e470aaeb061c6c0526e14f12bb89f753228b5a1,
and completed first-attempt original V5 run 43703208070 with exactly one
successful named read-only job. The newly qualified protected-main merge,
matching exact source tree, first-attempt full 8/8 regression, PR owner and
current main are checked from provider data before host inspection.

The original F139-HYBRID-V41-SOURCE-COMMIT owner comment 6883036903 is
independently re-read and validated with canonical JSON against the frozen
V37 source proof, original 1829 head and first-use=false/activation=false
restrictions. The original task is independently proved disabled using the
qualified, unweakened original owner guard. Under the original owner mutex,
Database.open_readonly and readiness.inspect_held_original verify the actual
V37 committed 1830 event, exact head hash, full detached cold backup and
preserved negative history. The task, issue policy, original content and
source main are checked again before a successful bounded receipt.

The new diagnostic-only release qualifier is separate from historical
readiness._release; the latter and all source-commit, backup, native
activation and scientific owner gates are unchanged.

## Allowed result and stop criteria

Success emits only F139_V38_ORIGINAL_LEDGER_COLD=PASS_READONLY_1830_COLD.
Negative result is one of AUTH_DENIED, PATH_OR_TASK_UNVERIFIED,
LEDGER_OR_COLD_UNVERIFIED, POSTCHECK_UNVERIFIED or UNCLASSIFIED.
No raw SQLite rows, filesystem paths, action arguments, SIDs, exception
text, tokens, sources or task metadata leave the Windows host. Every
negative fails closed. No replay of a consumed owner comment or uncertain
effect; never infer task restart authorization from a green CI or snapshot.

After exact-head 12/12 candidate Linux/Windows native/rehearsal, a
matching-tree protected-main merge and complete first-attempt 8/8 postmerge
regression, the owner may issue ONE fresh authenticated issue #807 comment:

F139-V38-LEDGER-COLD-READONLY-V1 <qualified-main-merge-sha> 6892848524

This authorizes read-only qualification only. Separate future owner
authorization and independent native acceptance are required for any
source transition, Hybrid lane policy update, or controller restart.
