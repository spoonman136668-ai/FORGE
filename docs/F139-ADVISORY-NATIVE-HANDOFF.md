# F139 — advisory to qualified native-development candidate handoff (development only)

## Why this bridge exists

FORGE's existing native info-per-compute advisory ranks frozen candidate hypotheses.
The live F139 owner accepts **only** owner-authored, single-commit/single-allowlisted-file
native development PRs under its original enabled source-pinned policy. The
advisory cannot create a code patch, attest first-use, or grant dispatch.

This staged bridge lets an owner-authored native PR carry an optional, bounded
`forge.infogain.advisory.v1` lineage record. **Source bytes and Git ancestry
remain the sole entrypoint to F139.** The PR itself is not authorized by the
ranking, and neither an annotation nor a code unit test is scientific evidence.

## First source-only gate

On the existing `f139.nci04_autonomy_feed.prepare_feed` path:

1. Verify exact source-pinned enabled F139 policy, owner-author identity,
   one parent, one changed allowlisted source file, original-before/after Git
   blob bytes, and no PR ref drift.
2. Only *after* that verification, parse an optional JSON PR description with
   `schema=forge.f139.advisory-pr-handoff.v1`. Ordinary prose retains the
   historical owner-only path. Malformed declared handoffs fail closed.
3. Require immutable matching lane, controller SHA, head commit, parent source,
   file path and SHA-256 of changed native bytes. The selected forecast must
   identify the **same head**, have positive estimated information and cost,
   declare non-authorizing flags and preserve/check source historical digest,
   including original NEGATIVE/INVALID/INDETERMINATE counts and consumed
   mechanisms/sources.
4. Store the bounded advisory identity in the feed's *source-evidence hash*
   and diagnostic candidate result, **without modifying the exact V1 native
   issue schema, admission queue, source pin, worker, or owner SQLite**.
   Candidate deduplication still keys original candidate code, not forecasts.

## Input form

The entire PR description is a JSON object with these exact outer keys:
`schema`, `lane`, `controller_source_sha`, `head_commit`,
`target_commit`, `path`, `after_sha256`, `candidate_id`, `decision`.

`decision` is the unmodified `infogain.Decision` JSON (including its
`selected`, `history_preserved`, immutable digests and explicit
non-authorizing flags). The selected candidate ID matches
`candidate_id`, and selected `source_sha` must equal the PR head commit.
The caller must freeze the recommendation **before observing the proposed
development worker outcome**. A PR author can still assert a fabricated
forecast; the bridge validates consistency, not independently signed origin.
It must never be interpreted as independent science provenance.

## Not included and not authorized

- **No autonomous code synthesis** from optimizer prose or synthetic
  recommendation fields. Only genuinely changed native code can be admitted.
  The candidate-code producer remains a separately qualified engineering
  capability; an empty owner-PR supply is still honestly reported as empty.
- No second scheduler, queue, controller, paid API, Cloudflare/CKB integration,
  scientific first-use, optimizer promotion or protected-ref mutations.
- No automatic merge or alteration of original running owner. This branch's
  code is inert until separate focused and full source qualification,
  protected merge, and a deliberate exact-source original-owner migration.
- Never replay failed native runs or treat a prospective advisory forecast as
  verified positive evidence.

## Advancement gate

Demonstrate the optional metadata path via focused adversarial unit tests,
both original-path and advisory-path source authentication, one full FORGE
regression, and a new authentic pre-outcome advisory-bearing PR on a fresh
unfamiliar mechanism. Original owner ledger/receipt custody and a natural
post-migration worker succession must be independently observed before
declaring unattended advisory-fed development operational.
