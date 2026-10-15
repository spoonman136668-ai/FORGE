# FORGE R27 — exact-head atomic source-promotion preflight (read-only)

## Why this gate exists

R21–R26 established genuine unattended GitHub-hosted source qualification, source-auditor handoff, branch-rule identity and source-pinned policy continuity. GitHub Actions still hides bypass-actor fields from its ephemeral token. These omissions must remain a **hard denial of merge authority**, not a reason to rebuild Cloudflare/FSA infrastructure or to pay for Codex reviews.

R27 extends the **existing main-branch** `.github/workflows/forge-automerge.yml` read-only auditor to perform a second native last-mile check. It creates **no new controller or scheduled job**; the already-existing schedule and `workflow_run` wake remain.

## Independent acceptance steps

For each eligible owned, non-draft `proposal/fsa*` PR, this program:

1. Freezes the exact full 40-character PR head, exact current protected main SHA, source branch and expected base; no shortcuts or user-supplied success labels.
2. Requires the existing R21 GitHub-GET audit to authenticate the limited Go-only source diff, native FSA-specific and public Linux/Windows workflow paths, exact-head event, successful job sets, and unchanged pinned R26 ruleset.
3. Authenticates native GitHub PR review states and refuses `CHANGES_REQUESTED`, `DISMISSED`, pending/unknown values; requires GitHub to report `mergeable=true` and `mergeable_state=clean`.
4. Reads the pinned ruleset twice and independently checks source head, PR branch/base, and main SHA again. Changed policy, main movement, PR staleness, unknown review state, missing workflow job, GitHub dirty mergeability, or unbounded API pagination => explicit denial.
5. Separately reports `SourceTestsQualified`, `PolicyAnchorUnchanged`, `FullRulesetVisible`, `NativeMergeabilityClean`, `NativeReviewsUnblocked`, and `HeadAndBaseStable`. **`MergeAuthorized=false` and `ScientificAuthority=false` under every outcome, even synthetic positive fixtures.**

There is **no** GitHub PUT/PATCH/POST/merge call, write-capable token, auto-merge authorization, scientific original execution, review-bot call, model selection, or additional workflow.

## What remains for eventual automatic promotion

A genuinely fresh, independently authenticated *complete* branch-ruleset witness (including bypass actors), a safe protected main/pull-request merge authority, and a separate real server-enforced merge transaction conditional on `expected_head_sha` and native GitHub checks. Positive **hypothetical** local fixtures and a passing last-mile observer do not grant those powers.

The R27 live first-use acceptance should show the same real source PR evaluated by automatically triggered FSA and public Go checks and then by the `workflow_run` main-branch observer, producing an explicit blocked outcome for redacted bypass actors. No new scientific hypothesis or Wingless/Yggdrasil experiment may be consumed for this engineering test.

The user will not change account settings. Keep Codex for exceptional engineering only. Preserve Cloudflare usage caps, independent research projects, and fail-closed scientific custody.
