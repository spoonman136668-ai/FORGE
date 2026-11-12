# V41 original-owner read-only acceptance on existing status route

Engineering-only addition to the existing `F139-V9-STATUS <main-sha>`
issue-comment job. It is not a new workflow, scheduler, controller, queue
or production release. No owner task is started, stopped, disabled or edited.

The original status job already checks task/SID/installed SHA and SQLite
quick_check. An additional step revalidates runner, SID, task definition,
original installed V40 worktree, exact main source and canonical SQLite path.
It invokes `nci04_v41_original_owner_status.py` with the current checked-out
main source but reads the original database exclusively in query-only mode.

The new source path checks the intact V40 original event chain from event1826,
spent model attempts, frozen negative receipts, 153 verified / 56 quarantined
tasks, original native activation and original owner mutex. The existing
provider GET verifier checks the exact complete 100+100+0 GitHub catalog,
original release and two-lane policy. The pending verifier requires exactly
one authentic, never-admitted Yggdrasil issue #1715 with unchanged candidate.
All source/policy reads are rechecked for drift after the mutex is released.

A busy original mutex, missing archives, changed source, issue drift, denied
GitHub GET, mismatched SID/task/source or a fabricated initialized SQLite
database must fail closed. No polling or retries are introduced. Source
qualification may fail independently from the last V9 status and is not
allowed to alter the running owner.

The output explicitly marks `original_cold_backup_qualified=false`,
`source_release_qualified=false`, `source_transition_authorized=false`,
`scientific_first_use=false`, `hybrid_admission=false`. This proves the
real Windows owner's **readiness evidence**, not the V41 cutover.

Actual recovery still requires original cold backup and ZIP/generator restore,
exact owner-approved release/comment, immutable successor ref, one-time #1715
escrow/source transition, same-task binary/source replacement and separate
first-use authorization.
