# H89 — V26-rooted original-owner source transition design

**State: DESIGN ONLY — DRAFT / NOT QUALIFIED / NOT APPROVED TO EXECUTE.**

This document defines a candidate source-transition architecture for the existing
original F139 Windows owner. It does not install code, create a release ref,
change the owner policy, stop the task, write SQLite, publish a model proposal,
dispatch a worker, or grant scientific authority.

## 1. Exact starting identities

| Item | Last authenticated identity |
|---|---|
| Installed original owner source | `49c7b15343bea3c201fb52b498d8c0f397384afe` |
| Protected FORGE main at this design checkpoint | `0810ecf3df6378bcbfe5239d30df836b7e12a602` |
| Owner policy | Issue #807; enabled; source pin remains the installed V26 SHA |
| Last read-only original ledger witness | seq 350; SHA-256 `17614edebb1b067de8112615637160e2bd7e71a4b3ac05dbab78fc360eba3d97` at 2026-10-31 15:32 UTC |
| Existing qualified model-free candidate | PR #1296; H83 `4ad7d77bfac2fa359ccaa8f0630aa1c419dc573a`; separate and inert |

**Freshness rule:** seq 350 is a historical witnessed checkpoint, not a current
transition preimage. Before any later source approval is generated, the original
owner must perform a new bounded read-only snapshot. The approval must bind the
actual event sequence and head hash returned at that time. Never reuse the
seq-350 preimage or the one-shot i1290 audit authorization.

The protected-main delta from installed V26 is currently 101 commits / 54 files.
It contains runtime/controller and workflow paths outside the original
research-only allowlist. This design does not call that delta research-only and
does not change the 80-commit / 48-file source-continuity guard.

## 2. Chosen release boundary: the existing immutable release-ref ruleset

Authenticated GitHub readback at this checkpoint confirms the already-existing
ruleset **#26049392**, name `FORGE F139 immutable owner release refs`:

- enforcement: `active`;
- target: branch;
- include: exactly `refs/heads/f139-owner-release-*`;
- exclude: empty;
- rules: `update` and `deletion`;
- bypass actors: empty.

This is a materially different trust boundary from protected `main`. The
proposed V26 successor source must be built from the original V26 commit, not
from the unrelated 101-commit / 54-file main ancestry. Its final target SHA
must be placed on one uniquely named `f139-owner-release-<target-sha>` ref
covered by this existing no-bypass ruleset. The ref must be read back by exact
name and commit SHA before any owner transition.

The ruleset protects an existing release ref from update/deletion; it does not
authorize its initial creation. Creation is a separate release-preflight action
and must occur only after exact-target qualification and explicit source-release
approval. This design did not create such a ref.

## 3. Source graph and trust model

The proposed graph is:

```
installed V26 source (49c7...)
        |
        | bounded, reviewed V26-based source patch
        v
candidate V26 successor source
        |
        | exact target-SHA Linux + Windows source qualification
        | hosted development rehearsal
        | mandatory full Linux + Windows regression
        v
immutable f139-owner-release-<target-sha> ref
        |
        | original-owner one-shot approval bound to fresh ledger head
        v
same original Windows owner / same SQLite DB / same SingleOwner mutex
        |
        | one atomic SOURCE_TRANSITION_ADMITTED event
        | cold verify, policy readback, same-task reactivation
        v
same original owner running exact target source
```

The target must not be synthesized from current `main`. All runtime source
changes needed for the target must be present in the V26-rooted target tree and
qualified at that exact tree identity. If the resulting target cannot be
qualified without relying on unrelated main-only files or workflows, stop and
resolve that dependency explicitly; do not silently merge main ancestry into
the release.

After transition, the deployed source identity is authenticated by the exact
immutable release ref and its source SHA, rather than by treating every later
protected-main advance as an implicit runtime migration. A future implementation
would need to change the original source-verification path to require all of:

1. the source SHA equals the original SQLite meta source pin;
2. the exact `f139-owner-release-<source-sha>` branch exists and points to
   that same SHA;
3. GitHub reports the branch protected and the active no-bypass release
   ruleset covers that exact ref;
4. a second readback confirms the ref did not move during validation;
5. the immutable target tree matches the qualified source manifest.

This would be a separate explicit release trust root. It is **not** permission
to weaken, skip, or widen `prove_protected_research_only_advance`. The existing
80/48 allowlist remains unchanged and continues to govern its research-only
main-advance use case.

## 4. Required V26 transition event and one-use approval

A new versioned event/approval pair is required; no existing V9, V19, V20, or
V25 schema is reusable because each is tied to a different predecessor source
and historical ledger shape.

The proposed schema names are:

- approval: `forge.f139.v26-to-release.source-transition-approval.v1`;
- event: `forge.f139.source-transition.v26-release.v1`.

The canonical approval should bind at minimum:

- exact `from_source_sha` = installed V26 SHA;
- exact `to_source_sha` = qualified immutable release target SHA;
- exact release-ref name and ruleset identity/readback digest;
- fresh original owner event-head sequence and SHA-256;
- exact original task name, trigger/action fingerprint, Windows SID and
  original database identity;
- authenticated one-time owner issue-comment ID and exact source-pinned
  command;
- complete target commit/tree, changed-path, changed-line and blob manifest;
- Linux, Windows, hosted rehearsal, full-regression and source-safety receipt
  identities, all bound to the same target SHA;
- independent cold-backup manifest and digest, backup location identity and
  cold-open verification receipt;
- counts/digests for all verified, quarantined, provider-failure, native
  terminal, renewal, proposal-validation and draft-publication history;
- explicit invariant values:
  `scientific_first_use=false`,
  `accepted_ref_mutations=0`,
  `paid_api_calls=0`,
  `new_controller=false`,
  `new_scheduler=false`,
  `new_queue=false`.

Every field must be exact-schema, canonical, non-null where required, and
cross-checked against the original database and authenticated GitHub reads.
No user-supplied counts or digests are trusted without recomputation.

## 5. Original-owner transition sequence

The eventual guarded transition must use the existing original Windows owner,
same task, same SID, same SQLite database and same SingleOwner mutex. It must
be a one-shot release workflow, not a scheduled workflow.

1. Validate the exact owner-authored issue #807 approval against the target SHA.
   Re-read the complete owner policy body and compare it before any update.
2. Verify the exact release branch, active ruleset #26049392, no bypass actors,
   target commit/tree and all qualification receipts.
3. Verify the installed original V26 task topology and principal. Refuse a
   changed SID, task arguments, task triggers, alternate task, active Python
   controller, dirty checkout, wrong DB path, or unexpected owner process.
4. Under the original owner's controlled quiescence window, acquire the same
   original SingleOwner mutex. Require no READY/active work and unchanged
   ledger head.
5. Create a cold backup outside the original database volume. Verify the backup
   digest, manifest, SQLite integrity and full SHA event chain. Cold-open the
   backup independently and compare its meta/event head to the live preimage.
   The recovery procedure must be rehearsed on a disposable clone before
   production use; a same-volume copy is not sufficient.
6. Re-read the original database and owner/task witness immediately before
   mutation. Fail if any preimage moved.
7. In one SQLite `BEGIN IMMEDIATE` transaction, validate the exact one-use
   approval, change only `meta.source_sha`, and append exactly one
   `SOURCE_TRANSITION_ADMITTED` event with the new schema. Cold-verify the
   whole chain, all historical task/event custody, the exact predecessor
   source and new release SHA before commit.
8. Close and independently reopen the original database read-only. Verify the
   same event head and target source. Only then update issue #807's source pin
   using compare-before-write, and re-read the entire policy body.
9. Resume the same original task and verify its executable path, task identity,
   owner SID, source SHA and ledger head. If post-mutation state is ambiguous,
   leave the task disabled and stop. Never replay the approval or source event.

No code path may automatically retry a database transition, Git ref mutation,
policy PATCH, task restart or ambiguous remote write.

## 6. Qualification required before any live transition

A V26 successor candidate must receive fresh exact-target evidence, not borrowed
H83 or PR #1328 receipts:

- focused transition schema and atomic transaction tests;
- negative tests for wrong predecessor, wrong target, stale ledger head,
  forged owner event, policy drift, task/SID drift, changed source manifest,
  missing/weak ruleset, release ref drift, backup mismatch, pending/active task,
  duplicate approval, duplicate event and replay;
- verifier-cold-reopen tests on a synthetic original-schema database;
- forced failure at every step around the transaction boundary proving full
  rollback before commit and fail-closed task hold after ambiguous post-commit
  state;
- exact target-SHA Linux native/source qualification;
- exact target-SHA Windows native/source qualification on the authorized
  qualified runner;
- hosted development rehearsal;
- mandatory full Linux and Windows repository regression/build;
- independent read-only original-owner preflight and backup/cold-open evidence.

Synthetic tests must label synthetic history and cannot stand in for the live
Windows owner, SQLite event chain, task/SID, credentials, or real backup.

## 7. Explicit non-goals

This transition only changes the source installed under the same original
development owner. It does not:

- activate scientific first-use or accept/promote Wingless/Yggdrasil results;
- authorize the H83 feeder or its optional mock publisher to write;
- authorize a new model request, draft publication, issue creation or worker
  dispatch;
- reset free-model budgets, reuse a terminal or replay the validated seq-350
  proposal;
- modify accepted refs, scientific thresholds, held-out data, model identity or
  evaluation splits;
- add a controller, scheduler, queue, worker, runner or competing authority;
- use a paid model API or expose credentials;
- merge unrelated current-main changes or widen the research-only continuity
  guard.

Wingless independent G26 review and G111 short-child resource accounting remain
separate gates. H83 remains a qualified but inert engineering candidate at its
own immutable SHA.

## 8. Current gate disposition

```
H89_DESIGN=PROPOSED
CURRENT_V26_SOURCE=49c7b15343bea3c201fb52b498d8c0f397384afe
LAST_READONLY_LEDGER_WITNESS=SEQ350 (HISTORICAL; NOT A FRESH PREIMAGE)
IMMUTABLE_RELEASE_RULESET=26049392 (ACTIVE; NO BYPASS)
CURRENT_V26_SUCCESSOR_TARGET=NONE
EXACT_TARGET_QUALIFICATION=NOT_STARTED
FRESH_OWNER_PREIMAGE=REQUIRED
OWNER_SOURCE_TRANSITION_APPROVAL=ABSENT
LIVE_SOURCE_TRANSITION=NOT_AUTHORIZED
SCIENTIFIC_FIRST_USE=FALSE
PROMOTION=HOLD
```

The next engineering gate is to implement this contract as an isolated V26-rooted
source transition schema, verifier, CLI and one-shot guarded release workflow,
then qualify the exact target. The deployment gate remains separate and requires
fresh owner evidence and explicit authorization.