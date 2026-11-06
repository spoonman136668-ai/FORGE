# FORGE native checkpoint lineage (read-only, development evidence)

**Applies independently to Wingless and Yggdrasil.** This extends the existing native evidence qualification; it does not change F139 original-owner/worker admission, repository scientific policies, source identity, first-use, controller, scheduler or accepted refs.

Both model repositories already ship `research.portable-checkpoint.v1` export/restore infrastructure, but their portability READMEs describe it as dormant. Their learned-state artifacts must first be traced to original run and custody. Do not invent an accepted model checkpoint or infer cumulative learning from unit tests or proposal generation.

Offline check against two independently retrieved, authenticated portable artifact directories:

```
python -B -m nativeevidence.model_lineage --parent PARENT_DIRECTORY --child CHILD_DIRECTORY --parent-pin AUTHENTICATED_PARENT_CHECKPOINT_SHA256 --child-pin AUTHENTICATED_CHILD_CHECKPOINT_SHA256
```

The read-only checker verifies each manifest, bounded file contents, SHA256 identities, replay-vector references, unchanged project-specific cognitive interface, explicit parent checkpoint digest, distinct experiment IDs, and non-authorizing custody flags. It returns a **source-authentication-unverified** status because passing caller-supplied pins cannot independently authenticate GitHub artifact custody.

**It does not restore a running native model or prove learning.** Even if learned parameter bytes changed, output keeps `independent_cold_process_restore`, `continued_training`, `retained_capability`, and `matched_control_improvement` as `UNVERIFIED`; no optimizer reward, source promotion, scientific first-use, or original-owner mutation is allowed.

Next, each project's existing authorized experiment owner must obtain a true learned checkpoint from a genuine development run, preserve it durably, restore in a separate cold process, continue training on non-leaked new public experiences, and measure retained old-task and new-task performance versus an equal-budget fresh-start control. Freeze seeds, splits, interfaces, controls and resource budgets before using the output for any scientific inference. Keep failed successors and parents separately addressable. No automatic acceptance or promotion.

This script is deliberately compatible with existing portable artifact layouts and the existing `native-task-feedback.yml` dual-OS testing, not a new engine or controller.
