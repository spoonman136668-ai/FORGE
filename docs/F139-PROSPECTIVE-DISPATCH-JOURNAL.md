# Prospective native dispatch journal

This source change records the existing owner's dispatch decision in its
existing SQLite SHA chain. It does not install a release or change policy #807.
The live original owner remains separately pinned to
`b8d571763e6035b6c7cc602de8c562449142c573` until its existing release process
qualifies and installs a successor.

## Ordering and identity

The ordinary native `run_once` path asks `Database.claim` to archive its
decision. Inside the same BEGIN IMMEDIATE transaction, before changing READY
to START_RISK, it reconstructs the complete admitted-native READY menu from
prior admission/start/quarantine events and checks it against current SQLite
rows. It preserves ticket, lane, candidate bytes hash, original target commit,
tree, path, intent, admission event and manifest identities. It records the
existing lexicographic first-READY policy and the owner's UTC clock claim.

`NATIVE_PROSPECTIVE_ASSIGNMENT` immediately precedes the matching
`BEFORE_DISPATCH_INTENT`. Both events and the task transition commit before
the provider callback. A failed claim rolls back all of them. Once claimed,
the existing sticky START_RISK/WAIT_PROVIDER behavior prevents replay; this
change does not add a remote operation, queue, scheduler, retry or controller.
Cold verification checks the original SHA chain, replays historical menus in
one pass, validates the exact policy/envelope and requires the adjacent start
intent to match the ticket and timestamp. Historical events are not rewritten.

The envelope's `assignment_event_sha256` binds the prior head, menu, policy,
ticket and clock claim. It is a context digest, not a circular claim about the
containing event's own hash. The actual event sequence/hash comes from the
existing owner SHA chain.

The assignment validator now uses the real 40-character Git owner source SHA,
while byte/content digests remain SHA-256. It accepts the existing owner's
fractional-second UTC format and rejects impossible calendar dates. Provider
composition tests cover both positive and retained-negative V2 diagnostics
without mocking either the provider verifier or the assignment join.

## What this evidence establishes

This is the **dispatch** menu, not the upstream candidate-generation or
publication menu. The current intake contract permits one READY admission at
a time, so a genuine current capture will normally contain one choice. Its
deterministic probability 10000 basis points is conditional on this admitted
menu. It is not a randomized propensity or evidence of unbiased exploration.
Already started and quarantined candidates stay spent and out of later menus.

Local pre-start ordering does not prove external clock accuracy, independent
pre-outcome archival, unseen source families, scientific improvement or honest
randomization. Existing PR tests and upstream generator observations are not
declared unseen. The current worker attempt has not started at this boundary.
All scientific acceptance, optimizer-training and dispatch-authority fields in
the data record remain false. The record grants no authority of its own.

The remaining development feedback work is to preserve upstream choice menus,
qualify independently sourced archival custody, and evaluate genuine task
outcomes against frozen development controls with CPU/memory accounting.
Regression PASS/test counts are diagnostics, not task-quality rewards.

## Qualification

Real isolated SQLite tests check atomic rollback, visibility from a second
connection before the provider callback, cold reopen, no replay, successor
eligibility and tamper rejection. They reuse the existing explicitly untrusted
owner fixtures; fixture success is not live-owner proof. Focused and affected
interface checks run alongside mandatory full Linux/Windows source regression,
Go vet/build and the existing native/rehearsal qualification jobs before any
source integration. Live capture requires separate evidence after an eligible
original-owner release transition; this source PR alone supplies none.
