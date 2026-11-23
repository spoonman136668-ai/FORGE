# FORGE operational simplification R4 — durable two-lane synthetic controller

**This is an actual native two-lane *synthetic* process lifecycle, not original science.** CKB-plane retains all existing scientific authority. No code path dispatches real Wingless/Yggdrasil originals, changes accepted refs, connects brokers or contacts production systems.

## What's newly implemented

`cyclecontroller.Run` executes exactly two pre-existing lane names, Wingless and Yggdrasil, in **parallel native child processes** (not the sequential R1 supervisor). It persists a write-once controller identity and a **generation intent before either worker process starts**. Each native worker already writes its own original-risk custody, signed STARTED and signed TERMINAL receipts. After both synthetic workers finish, the controller hashes the complete exact six evidence files, records one write-once terminal proof and rechecks **all previous generations**.

- 2 distinct processes execute simultaneously per generation, with distinct isolated lane workspaces and no science secrets.
- 1–4 bounded generations may follow successively. A later generation never starts until the preceding pair's signed synthetic worker evidence has been durably recorded and verified.
- A private `controller.active` exclusive-create lock prevents another cooperative controller process from concurrently starting the same root. Any interrupted, ambiguous or externally tampered original leaves a sticky lock requiring **independent investigation**, not automatic retry or deletion.
- Identities bind exact worker binary SHA-256, a frozen composite plan digest, immutable ordered lane names, generation ordinals, previous terminal hash and prior intent SHA. Every restarted run checks exact file counts, chronological journal chain, evidence files and the independently *provided* minimum completed count.
- The only returned result is `DURABLE_PARALLEL_SYNTHETIC_NO_SCIENCE`: counts, evidence chain head, zero real originals, `scientific_execution_authorized=false`, `accepted_ref_mutation=false`.
- The new scheduled/manual hosted workflow runs both lanes for two complete generations on native **Ubuntu and Windows**, then re-invokes the controller on the same root using an externally supplied minimum completion floor of two and requires an identical head. It uploads the full synthetic receipts and journal for inspection. The native execution stage has a five-minute orchestration ceiling.

## Negative acceptance

- Exact binary, frozen four-fixture combined digest, root directory name and fixed bounded generations required. No arbitrary command, script, science repository URL, broker credentials or extra flags.
- An incomplete intent, missing/tampered terminal, altered worker receipt, unrecognized directory, cross-lane missing evidence, corrupted journal, stale floor or concurrent controller prevents new worker starts.
- A worker timeout/uncertain output stops the controller and leaves the attempted generation **consumed or indeterminate**, not safely retryable. Synthetic evidence files are never deleted by the controller.
- Each lane's scientific-original count remains zero; the existing real runner/first-use paths are not imported into this synthetic executable.

## Critical limits (not yet operational science)

This is a **local filesystem** journal and cooperative interprocess exclusion, not an authenticated global distributed CAS. A privileged coordinated whole-directory rollback is not detectable without an independently held current signed head and monotonic floor. A new GitHub-hosted runner has an ephemeral filesystem; uploaded artifacts show persistence across a restart **within the same job** and provide later archival evidence, but do **not** automatically give the next job live monotonic shared state. The workers' per-invocation synthetic signing keys and random synthetic original IDs are not attested real scientific identities.

This stage closes a tangible integration gap (parallel workers, multiple automatic generations, write-before-dispatch intent, readback and restart) without prematurely transferring authority.

**Next gates:** content-addressed, independently authenticated real research-history importer; protected per-lane persistent controller across actual host restarts; exact once-only original intent and original scientific evidence validation; worker-side original fencing; two independent native real research adapters; combined fixed scientific budgets/preregistration/negative and sealed holdouts; full native regressions, three-way CKB owner-custody reconciliation, and final controlled cutover. It is unsafe to call these green synthetic tests independently autonomous science.
