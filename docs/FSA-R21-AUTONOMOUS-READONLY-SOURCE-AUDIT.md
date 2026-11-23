# R21 — Unattended, no-paid-review source qualification

**Objective:** Let FORGE mechanically qualify bounded source changes without requiring a human or Codex review at every cycle, while preserving scientific review, first-use controls, and separate operational promotion authority.

## Implementation

- Reuse the *existing* `.github/workflows/forge-automerge.yml` hourly/scheduled workflow and GitHub-hosted runner. Its name is historical: **R21 makes this source auditor strictly read-only**. The GitHub Actions job token has `contents: read`, `pull-requests: read`, and `actions: read`. There are no merge API calls, no branch changes and no controller proliferation. Schedule, concurrency, and owner scope are preserved.
- On the **trusted default-branch SHA** only, the auditor checks genuinely open, non-draft, same-repository `proposal/fsa*` PRs. It requires <=6 changes confined to flat `eligibility/*.go`, `startrecovery/*.go`, or `fsaadmission/*.go` source; checks exact head and base identity; rejects unknown pages and incomplete evidence.
- It verifies both the existing public Linux/Windows workflow and the separate **FSA-source** workflow at exactly the same head SHA, with exact workflow file path, triggering event, job identities, statuses, source branch, repository, and run attempts. PR comments, untrusted labels, synthetic review summaries and alternate candidate workflows confer no authority.
- The existing `.github/workflows/qualify-fsa-source.yml` now runs automatically on relevant PR paths in addition to retaining `workflow_dispatch`. It checks out the **exact proposed source commit**, verifies the owned current PR, checks the authentic fork-point diff, and executes focused Go tests, one full suite, vet, build, and Linux race tests on hosted Linux/Windows.
- The live branch ruleset check preserves a deliberately strict boundary. If the read-only GitHub Actions token omits `bypass_actors`, the result is `RULESET_BYPASS_VISIBILITY_MISSING`, **not** an invented zero-bypass assertion. The connected GitHub integration can see a zero-bypass policy, but this does not become an attestation automatically.

## Acceptance and boundaries

The R21 audit is **non-authorizing**: `MergeAuthorized=false` and `ScientificAuthority=false` always. Its source-only tests should prove positive qualification logic and fail-closed rejection. A successful read-only auditor run is not an accepted merge or scientific result.

GitHub main branch ruleset #25031517 continues to require strict Linux/Windows checks, dismiss stale reviews, resolve threads, and allow merge commits only. **No change to GitHub ruleset, independent scientific custody, research first-use, Wingless/Yggdrasil execution, Cloudflare, or CKB-plane.** Do not merge this workflow/policy change into `main` merely because its synthetic tests pass. It requires independently authenticated engineering acceptance and an authorized source workflow rollout; routine *future* bounded source changes then should not require a person.

## Next operational gate

After genuine R21 host qualification on its exact head, promote the source auditor into the default branch through the existing protected GitHub PR acceptance path. Then demonstrate one **genuine** auto-triggered FSA-source qualification and independent source audit on a fresh benign non-draft `proposal/fsa*` PR, without manual dispatch or paid model review. Keep server-side promotion disabled until full branch-rule visibility and a distinct atomic source-merge gate are accepted. Scientific original dispatch remains a separate authority.

**No GitHub source merge was attempted in R21.**
