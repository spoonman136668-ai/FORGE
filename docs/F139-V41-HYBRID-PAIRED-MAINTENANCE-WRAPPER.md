# Inactive V41→Hybrid paired original-owner pause/backup/resume wrapper

This is a **source-only** Windows PowerShell wrapper, not an enabled Actions
workflow or an installed task. It reuses only the existing
\`FORGE-F139-UnifiedController\` scheduled task and its existing
\`F139OriginalOwnerMutex\`; it never registers a task or adds a controller.
This file was NOT executed on the original owner workstation.

A future separately authorized original-owner workflow must receive a freshly
created **backup-only owner comment** on existing issue #807:
\`F139-HYBRID-V41-BACKUP-ONLY <current PR #1660 head SHA>\`.
The independent **later** owner approval must then read exactly:
\`F139-HYBRID-V41-PAUSE-RESUME <same SHA> <earlier backup comment ID>\`.
Only the second comment is eligible as the job event. The paired Python
gate checks distinct comment IDs, owner identity, chronological order,
original issue, exact V41 main, candidate PR head/base, existing two-lane
policy, original Windows task SID, clean installed V41 source, clean exact
candidate checkout and native ledger; it doubles original-provider readbacks.
Neither comment is a source migration or scientific first-use grant.

The wrapper's pre-mutation stage must pass the paired Python preflight,
existing task topology, original admin SID, source and ledger identity.
It takes one bounded original kernel lease, disables/stops *only the existing*
task and waits for owner process quiescence. The bounded backup subprocess
creates one fresh never-overwritten full cold bundle and verifies detached
SQLite, historic ZIPs, generator and negative-evidence bytes. On verified
zero-mutation original/owner/policy/main readbacks, it re-enables and
starts the SAME task. A pre-start failure may safely resume only when
the backup child has positively exited and the original state is verified
unchanged. If the effect is uncertain, it fails closed rather than replaying
an unclear task start. This wrapper has no task replacement, registration,
source transition, migration, policy edit, GitHub write, first-use or model
execution.

**NOT YET OPERATIONAL:** No event-driven workflow is connected, this script
is not present on protected main, and original-owner maintenance has not
been separately authorized. Source/fixture CI cannot qualify the actual
Windows owner pause or cold bundle. After exact-source dual-platform CI
the next qualified changes must connect the existing-owner-only event route
without introducing a new scheduler or controller and resolve release
eligibility when main advances. Original V41 owner and issue #807 policy
must remain unchanged until an authenticated owner-specific operation.
