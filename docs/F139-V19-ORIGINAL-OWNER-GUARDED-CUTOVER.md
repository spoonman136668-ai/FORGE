# F139 V19 — Guarded original Windows-owner cutover

**State: SOURCE-ONLY DRAFT, not merged, deployed, dispatched or approved to execute.**

This lane extends the qualified V18→V19 SQLite source-transition engine in #1056 without introducing a second controller or scheduler. The only runtime admission path is an explicit original-owner `transition-qualified-native-v19 --approval <file>` command. It requires an exact, canonical, owner-event-bound V18 SQLite read-only preflight; installed clean target commit; identical protected main; disabled legacy dispatcher; the same existing original Windows owner/profile; the same single-owner SQLite lock; and an atomic one-event V18→V19 source transition.

The workflow `.github/workflows/f139-v19-original-owner-cutover.yml` is **not scheduled** and has no automatic deployment on merge. Its only entry is a new source-pinned owner-authored comment on policy issue #807: `F139-V19-OWNER-CUTOVER <exact-protected-main-sha>`. The comment alone is not proof. The workflow denies a nonowner, rerun, wrong runner/SID, stale/dirty installed source, alternate scheduled task, wrong triggers, active Python controller, shifted policy body, wrong protected main, missing exact protected release branch, or weakened/no-bypass immutable release-ref ruleset.

Only once the existing task is disabled and its original processes are quiescent does the workflow fetch the exact source. It performs a **cold verified** SQLite backup, compares the backup event SHA head to the original, writes a SHA-256 receipt, checks readback, then attempts the explicit V19 one-event source transition and source-bound native reactivation. The original policy #807 pin changes only after the source transition and reactivation; task restart comes after policy and ledger readback. Before possible SQLite mutation, failure tries to restore the V18 checkout and original task; after mutation may have occurred, failure **leaves the existing task disabled**, not claiming rollback is proven or replay permitted.

The original owner policy must remain scientific_first_use=false, paid_model_calls=0, accepted_ref_mutations=0, new_controller=false, new_scheduler=false, new_queue=false. A successful source cutover does not activate V19 model-provider HTTP, write PRs to Wingless/Yggdrasil, prove ongoing training improvements, or authorize native scientific acceptance.

## Outstanding release requirements

All source and workflow test jobs must pass at the **exact final PR head** across native controller, hosted development, and full repository Linux and Windows. The release target must be created as a separately controlled immutable `f139-owner-release-<SHA>` branch covered by the existing ruleset, with no bypass actors. The original Windows owner must pass a genuine cold identity and task/backup inspection. Do not merge the stacked draft PRs, edit protected main or issue #807, create the release ref, or post the trigger comment merely because hosted tests passed. In particular, a hash-checked backup on the same drive is **not** a full disaster-recovery proof; no live rollback rehearsal is claimed.

Parent custody chain: #1052 clean V19 source integration → #1053 V18 owner read-only readiness → #1056 atomic V18→V19 transition engine → this source-only CLI/workflow gate.
