# V41-to-Hybrid original owner backup-only admission

This is a **source-only** original owner entry point. No Actions trigger is
connected; the currently installed FORGE controller remains the owner.
The prior original V41 maintenance approval was V40→V41 only. It is NOT
reusable authority for V41→Hybrid.

The new \`f139/nci04_v41_hybrid_owner_maintenance.py\` has explicit
\`--preflight-only\` and backup-only modes. Both require the existing original
owner runner, first-attempt issue-comment event #807 with exact owner text
\`F139-HYBRID-V41-BACKUP-ONLY <current PR #1660 head SHA>\`, double
provider readback of that comment, protected V41 main, current open PR head
and base, and the unchanged two-lane policy. The Git checkout executing the backup
must be clean and EXACTLY the current authenticated PR candidate SHA,
not an Actions synthetic merge ref or local uncommitted code. The user must authorize any
actual task pause/resume separately; a comment here is one authenticated,
scoped backup intent, NOT release or first-use authority.

The preflight reads the current original V41 event chain, active/ready state,
native slot activation, and original task SID / original source-root / DB
identity, but never disables the task. The backup mode refuses to run unless
the **existing** task is already genuinely disabled, its SID/source/DB are
correct, and no original controller Python child remains. It then exclusively
leases the *existing* original kernel lock, reuses the already qualified
current-V41 full cold-bundle creation plus detached restore, and checks all
resulting receipts and source/policy/comment readbacks again. The maintenance
caller must independently and safely perform an authorized temporary
task pause/resume with a bounded child timeout and a fail-closed recovery
fence. That caller has **not been connected or invoked**.

Both modes are inactive unless explicitly invoked by an appropriate future
owner workflow with the exact event. No new controller, scheduler, queue,
model first-use, scientific result, worker dispatch, policy edit, release
reference, SQLite schema migration, merge or original source transition.
Source CI does not authenticate the actual Windows task, and a fixture
must never be reported as a live owner backup.
