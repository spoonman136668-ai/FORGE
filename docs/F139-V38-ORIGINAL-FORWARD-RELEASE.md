# Original F139 V38 forward source release: one native owner, no new controller

## Status and motivation

The original F139 owner on FORGE-CODEX-REMOTE is disabled by its V37 hold,
with unchanged two-lane policy Wingless/Yggdrasil. The original V5 task
snapshot PASS F0000-U0000 was followed by authenticated read-only original
SQLite event 1830 and detached cold-backup acceptance PASS in original-owner
run 43707534359 (one attempt, no original mutations). Neither receipt
authorizes Hybrid admission or source commit.

The historical forward-readiness, backup, source-commit and postcommit
modules were present and source-qualified in FORGE but unregistered and
tied to old PR1759's protected-main identity. They cannot run against a
new main without falsifying the release source gate. This source PR pins
one new qualified release and registers four stages under ONE existing
original F139 owner workflow concurrency group, WITHOUT creating a
scheduler, controller, queue, worker or scientific first-use.

## Single release qualification

On PR #1772's exact source, prove PR owner, branch, merged protected main,
committed V37 source ancestor, same candidate+merge tree, all three
first-attempt full qualification workflows (public Linux/Windows, native
F139, hosted rehearsal), and first-attempt 8-job postmerge regression.
Any main, source, PR, custody or run drift FAILS CLOSED. Historical #1758
and #1759 releases are not retroactively reauthorized.

Source changes are limited to the new owner event workflow; the existing
forward-readiness release binding and its isolated synthetic tests; one
new scope test; this document; and G145/G148/G156 frozen source guards.
Original owner task/SQLite code, successor forward backup/cold bundle,
source-commit proof, postcommit logic, two-lane policy, and legacy
original live-install workflow remain byte-for-byte unchanged.

## Ordered native owner operations

Only AFTER full candidate CI, matching-tree merge, first-attempt main
CI, and fresh original owner/runner/issue-policy readback, execute
one original issue #807 event at a time:

1. F139-HYBRID-V41-FORWARD-READINESS <main-sha> 6883036903
   Authenticates frozen source event 1830 and current disabled original
   task and held detached cold backup. No mutation.
2. F139-HYBRID-V41-FORWARD-BACKUP <main-sha> <new-readiness-comment-id>
   New cold backup on the original host with independent restore and
   hash receipt, no original SQLite write or task start. This makes a new
   receipt, so never replay an uncertain backup attempt.
3. F139-HYBRID-V41-FORWARD-COMMIT <canonical-json>
   Only after reading and independently verifying the full backup
   receipt. The existing code admits precisely event 1831 as a
   forward source-only transaction; owner task remains disabled and
   policy unchanged. No replay of an uncertain commit.
4. F139-HYBRID-V41-FORWARD-POSTCOMMIT <main-sha> <new-commit-comment-id>
   Read-only verification of original event 1831, full cold backup,
   historical verified/quarantined negatives, original owner state,
   exact source and unchanged policy.

These operations do NOT authorize task activation, source checkout
retarget, schema migration, lane admission or scientific first-use.
Those require native independent qualification and owner policy
authorization after the event 1831 postcommit hold. Do not change
original SQLite or source without actual required receipts.

## Failure and recovery

All event routes are owner-only issue_comment:created, first-attempt
original runner only, GH_TOKEN read-only, no scheduled workflow.
The source commit is the only event that may write the original
SQLite; it is already guarded by single-owner mutex, disabled task,
frozen bundle/source hashes and complete postcommit readback.
Negative results are held and classified, never automatically
retried. Preserve the previous original V37 backup and 153 VERIFIED
and 56 QUARANTINED history.
