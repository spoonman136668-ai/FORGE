# Three-lane fair development intake — source qualification

## Scope and original source

Protected parent `c5cceb2a1d20794c6c07204b8edc4f8472fcacae`, tree
`38e67946a38ac50546871a4274e015a866b7a184`. This engineering change owns only
intake fairness and Hybrid pre-dispatch journal compatibility. No workflow,
G145 rule, model repository, source allowlist, owner policy or live DB changes.

## Reproduced defects and implementation

Without advisory steering, the original feeder returns after its first two
Wingless candidates and never inspects the third lane. With steering, the
ranker accepts only Wingless/Yggdrasil; Hybrid fails input validation. Finally,
an otherwise admitted Hybrid task fails the existing prospective assignment
validator before its dispatch intent can be recorded.

The existing feeder now authenticates its bounded per-project catalogs before
selection. It serves the least recently admitted eligible lane first, one
candidate per lane before allocating surplus places. The original verified
`NATIVE_DEVELOPMENT_ADMITTED` event order reconstructs service after restart;
no clock, counter, cursor, queue or new controller is introduced. Forecasts
rank candidates within each lane and cannot starve another eligible lane.
Previously admitted READY/in-flight tasks keep their original dispatch order.
Only the existing exact three development lane identities are accepted by the
prospective journal validator. Hybrid owner issues are deferred until the
explicit original-owner schema migration is present. Source/HMAC/migration,
two-slot, budget, no-replay and scientific fences are unchanged.

For continuously eligible lanes and successful admissions, each lane receives
one of every three admissions. This is an admission opportunity guarantee,
conditional on capacity and eligibility; it does not promise worker completion
or fabricate availability when provider custody is ambiguous.

## Engineering evidence and acceptance

`test_three_lane_fairness.py` covers real source-bound feeder contracts for all
three repositories, repeated backlog selection (24 places: 8 per lane), malformed
history, an unavailable lane, unchanged two-lane policy, and the existing real
SQLite/tick/restart path with a fixture provider. The latter proves two distinct
lanes in WAIT_PROVIDER, no duplicate dispatch on reopen, then Hybrid selection
after quarantining failed fixture providers. No synthetic terminal PASS is made.
Full exact-candidate Linux/Windows public tests, race/vet/build and original
controller/development rehearsals remain mandatory before protected merge.
These tests are engineering DEV, not live-provider or scientific measurements.

## Release and deployment boundary

PR #1648 merged the fair intake at `0e122eb8e571ddddee1dea4168cf18cfc7dc019d`.
Its exact candidate passed all 12 checks and full postmerge run `42613620494`.
PR #1651 subsequently qualified an explicitly operator-authorized exact G145
release route. Existing PR #1642 released the frozen worker blob
`74dd90e6d71da6b53898c7a80d5362f1b0e6af27` at protected-main merge
`89e14488ffeec348aac0c38dbd1a70c3dd0bf188`. Final candidate
`ffb18c8cb0d6e7284049fb857fff35f4c716b6e4` passed all 12 checks;
postmerge full regression `42633698447` and origin `42633698503` passed.
Earlier G145 failure `42602300389` and stale-event failure `42632280738` are
preserved negatives, superseded only by actual final-source qualification.
Generic workflow/harness rejection, ruleset `25031517`, required linux/windows
checks and no bypass remain intact. No original-owner cutover was performed.

Read-only original-owner run `42634108093` verified installed source
`42c70d74dd93ef90d0f4618fefefe2206b81eafe`, distinct from released main.
SQLite quick-check passed at event 1462; the existing task reported Running.
That is not full event-chain/provider reconciliation, mutex verification or
proof of activated two-slot/Hybrid schemas. See
`F139-THREE-LANE-RELEASE-READBACK.md` for the exact snapshot and deployment limit.
The current V39 cutover requires predecessor `54d556c3...`, not the installed
`42c70d74...`, and manipulates scheduled tasks. It cannot be repurposed here.
Original-owner migration and private Hybrid worker qualification require their
own verified scope; no restart, scheduling, replay or implicit opt-in is allowed.

Policy #807 currently pins `42c70d74dd93ef90d0f4618fefefe2206b81eafe` and only
Wingless/Yggdrasil. That policy is not proof of current installed source or
two-slot activation. The installed source is now read-back verified; slot activation and full
reconciliation remain unverified. This source work grants
no original-owner migration, scheduler operation, scientific first-use or GPU
preemption authority. Existing independent research and negative results remain
untouched; no learning, intelligence, throughput or cost superiority is claimed.
