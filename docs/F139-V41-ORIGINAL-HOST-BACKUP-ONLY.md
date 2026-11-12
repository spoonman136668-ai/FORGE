# F139 V41 original owner cold-backup-only route

Opt-in one-shot owner maintenance in the EXISTING G54 GitHub workflow
and existing FORGE-CODEX-REMOTE Windows runner. No new controller,
scheduler, queue, workflow, paid model request, model attempt, or first-use.

The job responds only to an exact OWNER-authored issue #807 comment:
F139-V41-COLD-BACKUP-ONLY <exact protected main commit>

It refuses to execute until the original task FORGE-F139-UnifiedController
is independently DISABLED, its original SID and task definition match,
its V40 worktree is clean and intact, and its original SQLite is at the
canonical LOCALAPPDATA path. The exclusive original kernel mutex must
succeed and the authenticated remote two-lane policy must remain on V40.
The workflow NEVER pauses, disables, starts, stops or edits the task.
The comment authorizes BACKUP ONLY, not owner quiescence or deployment.

The Python CLI double-reads the exact owner comment, preserves pending
Yggdrasil #1715, invokes the previously merged run-specific SQLite
online backup with provider ZIP and original generator custody, independently
restores the sealed bundle, and rechecks original ledger and remote
comment/policy/main. Private artifacts and credentials remain local,
never uploaded; logs contain digest-only receipts.

No genuine Windows owner maintenance was executed by this source change.
Actual original-owner acceptance requires the authorized task owner to
quiesce the original task and explicitly issue the scoped backup-only
comment after exact-SHA Linux/Windows CI. A successful cold backup does
not authorize live V41 source transition, model first-use, Hybrid
admission, or any reissue of pending #1715. Original owner remains V40.

The pre-existing G145/G148/G156 original Go regression guards now bind
this one owner-authored PR #1734, its exact base, protected original
workflow before/after blobs, seven-file source scope and negative controls.
No generic workflow changes or cache/harness bypass are permitted.

The maintenance entrypoint additionally denies staging unless this exact
PR #1734 is protected-merged and both first-attempt protected-main CI
families (full Linux/Windows regression and F73 cryptographic origin) have
succeeded on that same immutable main SHA. Actions permission is read-only.
It rechecks those identities after staging. CI receipts are never owner or
scientific authority.


## 2026-11-12 operator-authorized temporary same-task maintenance

The operator explicitly approved a temporary pause and resume of the
EXISTING F139 original Windows controller for private V41 backup and detached
restore ONLY. No source transition, new controller/scheduler/queue, policy
edit, scientific first-use, model call or Yggdrasil #1715 replay.

The same G54 job/runner now accepts an exact OWNER comment
F139-V41-PAUSE-BACKUP-RESUME <qualified protected main SHA>.
A new Windows wrapper verifies owner SID and administrator rights, clean
original V40 worktree, original two-lane policy, exact approved comment,
protected main and exact successful postmerge regression and origin checks
BEFORE disabling the one original task. It first acquires the existing
kernel mutex and waits for an idle tick. It then disables and stops ONLY
that task, verifies no original controller process remains, releases the
mutex to the existing V41 private backup and independent restore CLI, then
checks the original ledger head and policy are unchanged and starts the
SAME task exactly once.

If backup fails while the original ledger, source, policy and disabled task
are independently intact, the wrapper attempts a single safe resume. On
uncertain effects or a failed resume, it holds for manual verification; no
start is blindly retried. An Actions runner failure while paused cannot
promise recovery. A successful job requires a genuine Ready/Running owner.

The old backup-only comment is no longer an executable trigger; the new
PR #1735 and exact frozen G145/G148/G156 CI admission and postmerge CI must
pass before the owner maintenance comment is issued.

The private backup subprocess is bounded to 10 minutes with an explicit
process-tree termination and a separate 30-second exit confirmation. A
backup-child termination that cannot be proven never triggers owner resume.
The G54 job has a longer independent timeout; success still requires the
same original scheduled task to be running again.

## Pre-mutation original-Windows negative preserved and repaired

The first genuine original-runner maintenance job #43331020104 failed on
2026-11-12 before disabling the task: Python `pathlib.Path` is a factory,
while the runtime concrete WindowsPath is a subclass, so strict
`type(path) is Path` rejected the real canonical original database path.
PR #1736 replaces those two guards with `isinstance(path, Path)` without
relaxing canonical profile identity checks. A real OS-path fixture on both
platforms exercises the full authenticated preflight, verifies zero bytes
changed and keeps the earlier negative in provenance. The backup job is
NOT replayed on the failed run; only a separate exact qualified merge and
new owner comment can invoke a new one-shot maintenance attempt.
