# FORGE R8 — cross-hosted-runner synthetic checkpoint recovery

**Scope: actual separate GitHub-hosted runner jobs, synthetic-only.** This extends R4's same-runner restart qualification. It does not claim perpetual autonomy, cross-host linearizable state, science custody, owner migration, or scientific originals.

## New execution and recovery boundary

`cyclecontroller.RunAnchored` requires an externally retained **exact predecessor generation count and full terminal SHA256**, before permitting any additional native synthetic subprocess. It:

- Validates the original pinned worker binary SHA256, plan SHA256, lane ordering and existing frozen identity.
- Replays the complete immutable journal and every Wingless/Yggdrasil synthetic signed worker STARTED/TERMINAL file, checks previous hash chaining and the real file contents.
- Requires `observed_completed == externally_pinned_count` and `observed_last_terminal_sha256 == externally_pinned_head`. A restored older head, later unseen head, changed generation count, missing earlier terminal, tampered worker evidence, or different binary/plan fails closed. An uncertain recovery keeps a sticky exclusive lock; no original is silently rerun.
- Can advance only prospective synthetic generation numbers, with durable intent-before-dispatch and two separately isolated parallel child processes per generation.
- Returns `scientific_execution_authorized=false`, `accepted_ref_mutation=false`, `original_scientific_runs=0` and cannot run real science.

The original `Run` interface remains unchanged for preexisting synthetic tests; the more restrictive `RunAnchored` is required by the new transfer acceptance and accepts no null/zero head.

## Two different GitHub runner acceptance jobs

`.github/workflows/forge-cross-runner-synthetic-restore.yml` is triggered manually and on the exact source files changing on main:

1. **Producer** (ephemeral Ubuntu runner): compiles immutable synthetic worker and controller; launches both synthetic lanes through generations **1–2**. Creates a compressed snapshot of the worker binary, controller and complete journal, then publishes the archive SHA256, worker SHA256, frozen plan SHA256, completed count and exact terminal head through its immutable job output.
2. **Consumer** (new, independent Ubuntu runner): downloads the producer's artifact, checks its archive SHA256, verifies the exact source SHA-derived plan and worker binary fingerprint, unpacks the original journal, then calls `RunAnchored` with the externally passed **generation-2 terminal head and count**. Only if all evidence matches does it start generations **3–4** across the two lanes. A second `RunAnchored` call verifies generation 4 with an independent count/head and proves no additional dispatch.
3. Both jobs and the original journal are uploaded under distinct named GitHub Actions artifacts for later inspection; no privileged or write-scoped GitHub token, CKB runner, or KTRADE access is requested.

Separate Go adversarial tests restore a physical copy into a fresh directory and verify the same boundary, plus mismatched head, lower/higher ordinal floor, missing historical terminal, absent external head, sticky quarantine, and no worker dispatch after failed recovery. Full Linux tests/race/vet/build and native Windows tests/vet/build remain required on the exact merged tree.

## What this does NOT solve

GitHub Actions artifact uploads and sequential dependent jobs prove durability across **two ephemeral runner machines within one workflow**, but do not establish an independently durable monotonic journal across future scheduled workflows or protect against privileged entire archive rollback. Neither the source-side SHA256/job output nor the local lock is a separately signed live owner-revocation credential. The historical CKB S14 original remains consumed or indeterminate; do not rerun it. FORGE is not authorized to assume Wingless/Yggdrasil scientific ownership.

**Next operational gate:** recover a fully authenticated globally first-use ledger, qualify native real scientific worker side effects with one-owner lease fencing and original STARTED/TERMINAL receipts, then run actual independent disjoint-lane prospective science under a controlled authority cutover. Preserve existing working research until that gate is independently accepted.
