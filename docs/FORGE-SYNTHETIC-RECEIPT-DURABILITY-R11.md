# FORGE R11 — local signed worker receipt crash-durability repair

**Scope:** The existing fixed, synthetic-only worker. No scientific experiment is started and no FORGE/CKB research authority changes.

At the qualified R9/R10 source boundary, the worker issued write-once Ed25519 STARTED and TERMINAL files, used `Sync` on each file, and closed it; it did **not** sync the parent directory entry. The immutable attempt-journal module already synced its containing directory. R11 aligns the receipt writer with that existing local durability protocol: after exact write and file sync/close, open the parent directory, sync it, close it, and fail closed if any supported operation fails. As with `attemptjournal`, Windows does not provide universally supported directory fsync and explicitly retains that platform limit.

A missing/unreadable signed receipt after restart remains **irreversibly quarantined; never replay an original**. Added focused readback/write-once coverage. R11 does not prove power-loss durability on every filesystem, independent key provenance, worker-side epoch fencing, distributed linearizable custody, private CKB S14 reconciliation, or real scientific original acceptance.

**Qualification required:** Full Linux `go test -count=1 ./...`, race, vet and build; native Windows full tests, vet and build at the exact branch head. Existing two-lane synthetic controller/readback, restart/no-replay and cross-runner qualification should remain green. Do not merge without both platforms passing and a pinned head/tree review.
