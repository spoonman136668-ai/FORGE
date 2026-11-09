# Exact Hybrid workflow release qualification

## Scoped authorization and source freeze

On November 9 the operator explicitly authorized the separate narrowly scoped
workflow-release mechanism after the three-lane integration stopped at G145.
This is engineering qualification authority for the exact worker, not original
owner migration, policy opt-in, scheduling, training, scientific first-use or
model promotion authority. Existing isolation and project owners are preserved.

Protected original main: `0e122eb8e571ddddee1dea4168cf18cfc7dc019d`, tree
`4dd3ad8fcd4ab039192994ebfa679ced30af6b1a`; full eight-job postmerge PASS
`42613620494`, independent origin PASS `42613620716`.
Governance branch: `engineering/f139-exact-worker-release-scope-20261109`.
Exactly five files: this document, `scripts/check_rar_g145_pr_scope.py`,
`scripts/check_rar_g148_go_cache.py`, `scripts/check_rar_g156_dynamic_base_cache.py`,
and `f139/test_hybrid_workflow_release_scope.py`. The existing G145 frozen-scope
mechanism admits this exact branch/base/path set for its own full qualification.
The G148/G156 adapters recognize only these authenticated admission modes;
their compiler cache keys, optional base-cache custody and full tests are unchanged.
No workflow, original Go command, memory/package control, cache semantics,
required check, ruleset, accepted ref or runtime configuration changes here.

## Worker-only admission after this mechanism is qualified and merged

Only existing FORGE PR **#1642**, owner-authored by `spoonman136668-ai`, from
`release/f139-hybrid-qualified-worker-governance-20261109` into same-repo main.
The authenticated GitHub event must match checked-out head, base/ref and repo
identities. Exact event-main must be an ancestor of the candidate and descend
from the source anchor above. The complete non-renamed diff must contain only
`.github/workflows/forge-f139-development-worker.yml`, regular mode `100644`:

- Original blob: `8eab7972ba1b30eabf1e38477aff60b598cdeb2f`.
- Independently qualified Hybrid blob: `74dd90e6d71da6b53898c7a80d5362f1b0e6af27`.

Any byte/mode drift, other PR/branch, harness or additional-file change, missing
source, unrelated base or already-released base fails closed. The old-to-new
blob requirement makes this a single source transition; this cannot authorize
a second workflow change after release. Generic PR workflow/harness rejection
and all historical frozen scopes remain intact. G145 positive/negative controls
run in both unchanged full-Go qualifier entrypoints; F139 regression exercises
the actual GitHub event router and additional malformed/provenance negatives.

## Qualification sequence

1. Full exact governance candidate public Linux/Windows regression including
   Go tests, Linux race, vet/build, plus original controller and hosted DEV
   rehearsals. Protected merge with expected head only after all checks pass.
2. Verify postmerge full regression and independent origin. Synchronize existing
   #1642 with this protected source, preserving its one exact worker blob and
   no other delta. Qualify the actual final worker candidate on both platforms;
   earlier candidate receipts cannot substitute for this source.
3. Protected expected-head merge only after complete PASS; verify final main
   tree, worker blob, full postmerge regression and independent origin.
4. Stop before live owner/source/schema/policy changes unless independently
   verified authority permits those exact operations. Reconcile original mutex,
   ledger and provider receipts, original source continuity, actual two-slot
   activation and isolated Hybrid source access before any owner activation.

Engineering CI eligibility is not permission to execute a controller or model.
No bypass actor, fabricated check, force merge, scientific episode, GPU job,
new controller/queue/scheduler or paid API is part of either source release.
Three-lane fairness remains the already-qualified #1648 implementation. Actual
signed Hybrid receipts, contention, latency and throughput need authorized live
qualification; no intelligence or performance gain is inferred from these tests.
