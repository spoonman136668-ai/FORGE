# F139 G38 — Original-owner V2 terminal custody, crash-safe and versioned

G37 PR #957 completed all eight hosted Linux/Windows CI checks at
2868481da6c1a6803ea31584a4eb8d95312e19f8. G38 is source-only and
is NOT an original-owner source migration or a live experiment.

The existing F139 controller now routes only a genuinely fresh, frozen
G13 Yggdrasil V2 ticket to a separate provider result handler. That handler
reconstructs original V1/native signed admissions from existing immutable
SQLite owner admission and claim events, creates original-owner G31
run-bound V2 permits, authenticates the real GitHub workflow/run/jobs and
downloaded outer artifacts with G35, and independently rechecks both
inner V2 receipts and original issue/SQLite event chain with G32.

G38 persists exact original GitHub outer ZIP bytes using the existing
fsync and exact-byte readback recovery store before one original SQLite
transaction. Within that single transaction a successful development run
becomes VERIFIED with the usual provider terminal event; an authentic
negative report becomes QUARANTINED with the existing negative receipt
and no attempt replay. Both append the G38 versioned original V2 event.
Every cold Database.verify now checks event uniqueness, task status,
both outer GitHub archive hashes and the original manifest bytes.

Tests run against disposable original SQLite and synthetic provider fixture
bytes. Existing G35 tests independently exercise the GitHub API adapter.
This is NOT proof that an actual V2 original experiment was dispatched;
do not use these fixtures to claim autonomy is restored.

**Production hold remains:** G37 requires source-pinned authorization and
a separately qualified V2 terminal writer before dispatching V2. These
flags are NOT set here. G38 is not published on main and must still pass
all hosted Windows/Linux regressions, original-owner exclusive mutex
and genuine source transition custody. Its first new original-provider
result must be observed on an ordinary unattended tick and followed by
a genuinely new successor, without manual replay.

No G1/G3/#907 retry, no new controller/task/scheduler, no paid API and no
scientific FSA first-use. Failure to authenticate an interrupted or
incomplete provider run leaves its task active, never falsely VERIFIED.
