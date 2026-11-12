# F139 V41 original-owner approval intent verifier (inert)

**Source-only development.** This module does not authorize, install, approve
a production release, append an event, reissue an issue or create an owner
task. It is a typed, GET-only *proposed owner-comment* comparison to support
a future V40→V41 release without reusing V39→V40 approval evidence.

## Original owner frozen boundary

- V40 original installed SHA: \`2c7caad5a4502d4b874a11d57207a35cf033eb08\`.
- Last direct Windows readback: [run #43198090257](https://github.com/spoonman136668-ai/FORGE/actions/runs/43198090257), original event 1826 / \`71fd4554315093d74f5a9968b4766191413cfd18d6b1ce81863f8451d379d769\`, 153 verified, 56 quarantined, zero active/ready, continued 200-issue catalog stall.
- Pending issue [#1715](https://github.com/spoonman136668-ai/FORGE/issues/1715) remains unadmitted and source-bound. It may not silently disappear or be replayed.
- Current protected main: \`51389291ac77e5caaa0e3a20eacaef80261d49f8\` at creation. Future target must be re-read, not inferred from this date.

## What this verifier adds

\`inspect_locked_original\` invokes existing authentic *read-only* source,
SQLite cold copy and pending-issue checks, all under the original owner mutex.
It then demands an **individually owner-authored, canonical, source/policy
bound GitHub issue #807 comment**, checked with two independent GET passes,
binding the exact live ledger head, snapshot/main SHA, original 1715 identity,
an explicitly chosen once-only pending disposition, original task identity
hashes and specific qualification artifact/run identities. Any drift denies.

The synthetic unit tests do **not** run this on Windows. A passing synthetic
comparison cannot establish an authentic Windows SID, backup, owner approval,
pending disposition, protected release, signed artifact or live acceptance.

## Strict non-effects and later prerequisites

All verifier returns mark \`source_transition_authorized=false\`,
\`pending_disposition_implemented=false\`, \`original_owner_release_qualified=false\`,
\`reissue_authorized=false\`, \`scientific_first_use=false\` and
\`hybrid_admission=false\`. Even an authentic comment is **owner intent only**,
not sufficient authorization to execute a release.

A later independently owner-qualified mechanism must verify the actual
original Windows SID/task/lease/backup/build/cold restore, independently
authenticate signed receipt and release ref, implement a crash-safe once-only
disposition for unadmitted #1715, and require fresh explicit owner approval
before any same-task source transition. No new controllers, schedulers, queues,
paid models, external science first-use or accepted model ref changes.
