# G145 — Restore original full Go qualification for unrelated FORGE pull requests

## Source/owner freeze (before implementation)
- **Protected main parent:** `69421a9d82bfb7b374d6635d3c60d7e41bfaf3b2`, after G144 #1609 merged. Original qualifying Linux script is `scripts/check_rar_g141_parallel_go.py`, blob `2e821898a5d3cd8bdaf9760b5bd8cb27923d45ca`.
- **Single implementation change:** that existing script's *pull-request admission check* only. Plus this protocol document. No workflows, Go tests, runtime code, controls, owner, FSA, research first-use, branches outside G145, or project science changed.
- **Bug:** Current G141/G144 source-scoped branch allowlist rejects ALL ordinary `pull_request` branches before running full Go test/race, preventing unchanged original qualification of independent FORGE work such as Eureka F4/F5/F6. This is a CI infrastructure defect, not an engineering failure of those packages.

## Frozen hypothesis
Allow same-repository, unchanged-original-harness PR candidates targeting protected `main` to run the **existing unchanged complete Linux original regular + race tests**, retaining all G141 memory admission (cgroup v2 <=4GiB), exact HEAD/tree/worktree, full 130+ package inventory, Go test cache disabled, package parity, vet/build and required Linux aggregate AND. Special historically authorized G141/G144 branch cases keep their old exact source-scopes untouched. G145's own branch is a *new single exact frozen source scope* for this one bounded fix; not a new general authority.

**Generic PR admission requirements (all mandatory):** GitHub `pull_request` event, exact GitHub event-path source provenance, base named `main` in `spoonman136668-ai/FORGE`, same-repo head, head SHA matching checked-out `HEAD` and `FORGE_G141_HEAD`, event head ref matching `GITHUB_HEAD_REF`, strict 40-hex base/sha identity, base SHA present and actual **ancestor** of the candidate SHA in the checkout (no unverified remote fetch), nonempty bounded diff from exact base to candidate. Forbid any ordinary PR changes to `.github/workflows/` or `scripts/check_rar_g141_parallel_go.py`, `scripts/check_rar_g144_windows_go.py` or new `scripts/check_rar_*.py` harness files. Detect rename/deletion using `git diff --no-renames --name-only`. A branch with insufficient ancestry must rebase/sync to main; no fallback to untrusted base selection. Changes to original test bodies may still be reviewed by the original standing guards and PR/FSA policies; this patch grants *engineering qualification only*, no permission to merge or execute.

**G145 self-admission:** Exact branch `engineering/g145-generic-pr-original-qualification-20261108`, base `69421a9d82bfb7b374d6635d3c60d7e41bfaf3b2`, exact two changed files `scripts/check_rar_g141_parallel_go.py` and `docs/FORGE-G145-GENERIC-PR-QUALIFICATION.md`. Its own acceptance does not authorize other workflow or source edits.

## Negative controls (automatic source-side validation)
- Accept a representative ordinary source-only Go repair PR changed-file set.
- Reject blank/too-large/duplicate path sets, CI/workflow/script alterations, rename/deletion of protected files, non-main base, foreign/fork head, mismatched event identity, missing base SHA, nonancestor/stale base, spoofed `GITHUB_HEAD_REF`, and non-SHA source.
- Existing G141 and G144 frozen development scopes still exact-match only; all other unknown harness-editing branches rejected.
- Keep original complete test/race *commands, ordering, flags*, Go vet/build, source cleanliness, memory/timeout/package controls **byte-identical**. No skip, no retry masking, no added service, paid API or owner mutation.

## Engineering acceptance
1. First G145 exact-head full original GitHub Actions qualification PASS for **all eight required jobs** (`linux_f139`, `linux_native`, `linux_genenv`, `linux`, `windows_f139`, `windows_native`, `windows_genenv`, `windows`). G141 scope side must show admitted mode and uninterrupted original Go test+race, not a skipped branch.
2. Confirm no original Go/Python test or workflow bytes changed; protected main remained parent SHA and G144 postmerge baseline qualified before merge. Merge solely under verified existing FORGE engineering authority, then verify postmerge original full regression and origin.
3. Then re-anchor F4 and F5–F6 draft PR heads on new main without loss of original source, run mandatory full exact-head Linux+Windows regression and report actual F6 development metrics. Do not silently call a new tree qualified because its parent passed.

**SCIENCE:** Unverified. **DEPLOYMENT:** Original owner untouched, only CI guard if merged. **Eureka:** source-only drafts and separate research continue; no automated controller integration and no scientific first-use.
