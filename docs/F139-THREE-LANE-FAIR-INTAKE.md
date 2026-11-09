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

PR #1642 remains draft at `10115c560338f5b0a0e9036d30376669d07962a0`.
Its only changed file is `.github/workflows/forge-f139-development-worker.yml`,
blob `74dd90e6d71da6b53898c7a80d5362f1b0e6af27`. Required public run
`42602300389` fails G145 on both OSes before complete Go qualification. Current
G145 frozen scopes contain no Hybrid release exception. Main ruleset `25031517`
requires successful linux/windows checks, strict source currency and no bypass.
The existing V39 original-owner cutover is not a generic workflow-source release
route and manipulates scheduled tasks; it must not be repurposed here.

The scoped maintainer must supply an existing independently authorized release
route that admits this exact workflow blob while retaining G145. Under current
rules none was found; do not add a self-authorizing harness exception, retarget
to evade qualification, force merge or change protections. Requalify the actual
final release candidate on Linux/Windows, including complete Go regression and
build. Then, only under verified exact-operation original-owner authority:
reconcile original ledger/provider receipts and mutex, perform qualified source
transition, verify/explicitly migrate two slots, migrate Hybrid schema, opt in
policy #807 to the exact source, prove scoped private-project worker access,
then collect real signed per-lane terminal receipts and contention measurements.

Policy #807 currently pins `42c70d74dd93ef90d0f4618fefefe2206b81eafe` and only
Wingless/Yggdrasil. That policy is not proof of current installed source or
two-slot activation. Those deployment facts remain unverified. This PR grants
no original-owner migration, scheduler operation, scientific first-use or GPU
preemption authority. Existing independent research and negative results remain
untouched; no learning, intelligence, throughput or cost superiority is claimed.
