# FSA R5 — same-instance witness high-water and poison fence

**Status:** source-only, non-deployed, non-executing.

The independently signed witness store previously verified the full on-disk chain on every read, but a complete trailing receipt could be deleted and leave an internally valid older prefix. A separately updated, operator-pinned minimum revision is still mandatory on every restart, but **while the same store instance remains alive** it can additionally fail closed against a rollback of a revision it has already served or persisted.

The `fsawitnessstore.Store` now serializes reads and append operations under a process mutex, maintains the highest observed signed revision/sequence/head/signature and refuses a decrease or same-revision substitution. A storage-integrity failure or ambiguous write poisons that running store instance. It cannot automatically clear poison by recreating or restoring a file; a new instance must receive an independently authenticated minimum revision and validate its on-disk receipts.

Synthetic tests exercise complete-tail deletion after successful append, corruption after an authenticated read, continued rejection after path restoration, blocked append from poisoned process and independently pinned fresh open. Existing competing-append tests remain required.

## Limitations

Process-local memory is not a separate failure domain and does not survive crash, power loss or service replacement. A new instance supplied a stale external minimum revision can still accept a valid rolled-back prefix; this change DOES NOT solve privileged rollback, full disk restore, physical durability, multi-host fencing, or credential custody. A second process with its own instance also lacks this in-memory knowledge.

No signer, HTTP mutation handler, CAS admission, worker launch, original replay, scheduler, queue consumer, CKB-plane/KTRADE controller write or production activation is introduced. FORGE autonomy remains blocked pending physical independent trust, atomic worker-side epoch enforcement and full cutover qualification.
