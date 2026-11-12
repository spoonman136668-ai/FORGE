# R17: full-object-ID source-review admission (non-authorizing)

The current `.github/workflows/forge-automerge.yml` deliberately stops before
merging: Codex issue-comment summaries provide only abbreviated review
references. An issue comment is not GitHub's authenticated full-commit PR review.

`fsamergeattest.Check` is an offline, pure source predicate requiring:

- Exact 40-character GitHub PR commit SHA and a GitHub-native Codex bot
  `APPROVED` review with precisely the same full `commit_id`.
- Same-repository, operator-owned, non-draft `proposal/fsa*` source-only PR
  to `main`, with a complete changed-file record.
- Successful same-head Linux and Windows **jobs** and a qualifying FSA workflow.
- Exhaustively collected reviews, inline comments, changed files, workflow
  runs and review threads, with no unresolved findings, requested changes or
  incomplete/human review threads.

A short SHA, old review, bot issue-comment summary or locally manufactured
attestation does not qualify independent evidence. Synthetic positive tests
only prove rejection/selection logic, not authentic GitHub review identity.

**No operational authority:** `MergeAuthorized` is always false. This
package does not access the network, create a scheduler, launch scientific
originals, touch first-use records, mutate CKB-plane, or merge PRs.

Next bounded gate: an independently qualified live REST/GraphQL evidence
collector that verifies real full-OID native reviews and complete pagination,
followed by a pre-merge head/rules recheck through the existing authorized
source-merge path. Leave the scheduled workflow's hard stop intact until
that integration is separately qualified. The engineering fast path is
content-addressed foundation verification, focused tests, then one full
repository regression on both Linux and Windows.
