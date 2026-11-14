# V41 → public Hybrid protected-main source bridge (read-only; inactive)

This module resolves the historical mismatch between an \`issue_comment\`
workflow's **protected-main** \`GITHUB_SHA\` and the open PR #1660 head.
The original V41 Windows task and original SQLite source remain frozen at
\`1a40fe4e3ec6e93a1631d59863b95e90981d734e\` during a later authorized
maintenance operation, but the executable owner-maintenance source must be
**merged, protected main**, not untrusted PR code.

\`f139/nci04_v41_hybrid_protected_main.py\` is a read-only source trust gate:
it requires exact first-attempt original-owner issue-comment provenance,
the protected-main SHA equal the executing source, merged PR #1660 owned by
\`spoonman136668-ai\` with that exact merge commit, historical V41 base,
authenticated commit tree, and four distinct terminal successful postmerge
push workflows for the same SHA (no retries, duplicates or other actors).
It re-reads main/PR/tree after CI and fails closed on drift. The exact main
commit cannot be known until a separately authorized merge; the gate does
not attempt to guess it.

The current owner task is not retargeted; issue #807 remains two lanes.
This is **not** a new controller, workflow, task or release authorization.
Protected main must first contain this code and the future appropriate
original-owner workflow, with full exact-main regression. A future paired
maintenance request has to point to the new merged protected-main SHA, not
the historical PR head. Owner pause/resume and actual backup are still
separately authorized; existing PR-open source validators cannot be reused
as live main execution authority.

No original-owner task interruption, SQLite, signed worker, source/schema
transition, policy admission, deployment or scientific first-use is permitted
by this source-only component.
