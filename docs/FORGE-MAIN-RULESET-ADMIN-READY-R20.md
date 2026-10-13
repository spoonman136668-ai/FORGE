# FORGE R20 — administrator-ready main ruleset; no settings change

Frozen engineering base: `3e94421896f32ffde4a3800834214a2ee7605207`.

## Live observed blocker

FORGE's exact-main branch readback returns `protected=false` and `rulesets=[]` (see R19 and issue #175). The accessible GitHub connector has **no repository-administration write action**, and GitHub REST `branches/main/protection` returned 403 `Resource not accessible by integration`. Therefore this engineering change **cannot install branch protection** or truthfully qualify it. A hosted `GITHUB_TOKEN` with contents-read-only/checks-read-only will not acquire `Administration:write` automatically.

## Proposed policy, not yet installed

`reference/governance/forge-main-ruleset-proposal.json` is an exact GitHub repository branch-ruleset request:

- Applies exclusively to `refs/heads/main` at **active** enforcement, with no bypass actors
- Blocks deletion and force pushes (`non_fast_forward`)
- Requires merge PRs and all review conversations resolved; sets **zero human review approvals** so an independently qualified automation can continue merging without routine operator clicks
- Requires **both** `linux` and `windows` source qualification check contexts, each exclusively from the GitHub Actions application (integration ID **15368**), with strict up-to-date source checking
- Does not list the path-filtered six-original/archive diagnostic workflows as universally required checks; those run only on relevant changes, so requiring them globally would create deadlocks. Other scientific custody and runtime gates remain independent.

The required contexts and GitHub Actions app identity were read directly from the public exact-main GitHub Check Runs API on `3e94421896f32ffde4a3800834214a2ee7605207`. This proves the contexts exist, **not** that GitHub enforces them today. The dedicated R20 read-only workflow rechecks the actual main SHA, contexts, successful check outcomes and app integration, and archives raw API evidence. Negative unit tests reject tampered plans, bypass actors, wrong status names, wrong app, failed/stale checks, and duplicated metadata.

## Single real administrator operation required

A repository administrator with `Administration:write` may apply the reviewed file *as a proposal* after confirming that the desired no-human-approval PR rule suits this repository:

```sh
gh api --method POST repos/spoonman136668-ai/FORGE/rulesets \
  --input reference/governance/forge-main-ruleset-proposal.json
```

This command is **documentation only**, not executed by any workflow or this engineering PR. Never paste or commit personal access tokens; use an already authorized GitHub account and current repository branch. If an applicable policy already exists, update and reconcile it instead of creating overlapping/conflicting rules.

After the admin operation, independently inspect `branches/main`, `rulesets`, the **full details** for each applicable ruleset, bypass actors, status source app and current protection applicability. Test that an unauthorized direct push/force push/delete or a deliberately failing PR cannot update `main` using a controlled nonproduction setup or permitted safe negative test. Record actual GitHub denials. A green CI run, policy preview, successful file validation or active rule name is insufficient. Keep #175 open until real enforcement evidence passes.

## Other cutover denials remain

No original experiment starts, replay, CKB/KTRADE writes, acceptance promotion, scheduler, paid API or scientific authority transfer. Independent physical FSA (#20), consumed-first-use/CKB S14 and worker fencing (#83), real prospective scientific generations and a 24-hour unattended soak must independently pass before any FORGE takeover.
