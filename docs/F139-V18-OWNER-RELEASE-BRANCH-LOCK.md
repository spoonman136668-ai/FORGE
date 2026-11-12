# F139 V18 — enforce immutable owner-release refs

**Status:** administrator-ready proposal; **not installed**. This document does
not grant source, model, worker, or scientific execution authority.

## Verified original state (2026-10-28)

- Original deployed F139 V17 and protected `main`:
  `3775bed30891ff748197a539afe5b92813680e26`.
- The combined V18 original-owner release workflow in draft FORGE #1035,
  commit `9f4fa2f12e7f7373cdfc68233058de44bf36d572`,
  passed all three Linux/Windows controller/public/hosted workflows.
- Candidate release branch
  `f139-owner-release-9f4fa2f12e7f7373cdfc68233058de44bf36d572`
  exists at the matching SHA, **but GitHub reports `protected=false`**.
- The scoped candidate in
  `reference/governance/f139-owner-release-ref-ruleset-proposal.json`
  is **not applied**. The connected engineering GitHub App cannot write
  repository administration; a read-only GET to branch protection returns
  `403 Resource not accessible by integration`.
- The existing active main ruleset (ID `25031517`) applies exclusively
  to `refs/heads/main`; it must remain untouched.

## Precisely scoped administrator operation

The payload creates **one** active branch ruleset with **no bypass actors**,
matching only `refs/heads/f139-owner-release-*`. It blocks updates and
deletions of those release branches after creation; it does not block creation,
alter main, change owner policy #807, or modify any source/ledger. A repository
administrator with **Administration:write** can perform this operation using
their pre-existing authenticated GitHub CLI session:

```powershell
gh api --method POST repos/spoonman136668-ai/FORGE/rulesets --input reference/governance/f139-owner-release-ref-ruleset-proposal.json
```

Run the command from a clean checkout of the **qualified governance proposal**,
not from the live Windows F139 controller's installed source directory.
Do **not** create a duplicate if a matching rule already exists; reconcile it
instead. Never put tokens into chat, files, workflows or issue comments.

### Independent verification before any owner-cutover event

1. Query `GET /repos/spoonman136668-ai/FORGE/rulesets` and the new ruleset
   detail: enforcement must be **active**, target **branch**, include exactly
   `refs/heads/f139-owner-release-*`, have **zero** bypass actors, and require
   both `update` and `deletion` restrictions.
2. Query both the existing exact-SHA release branch and
   `branches/main`: release SHA must still be
   `9f4fa2f12e7f7373cdfc68233058de44bf36d572`,
   release `protected=true`, and original main still has its separately
   enforced protections.
3. Observe an independently denied, **non-destructive** attempt to update a
   *dedicated test* branch matching the same release pattern, if an
   administrator can safely stage this. Never use the real release ref as a
   negative test and do not delete any real branch.
4. Recheck live Windows F139 owner read-only: original SQLite integrity,
   owner SID/process, source pin, event head, no READY/active work, historical
   negative custody and no spent free-model replay.
5. **Only after** a fully qualified combined exact target has been merged into
   protected main, separately pinned to an immutable release ref, and
   independently approved, an exact `F139-V18-OWNER-CUTOVER <SHA>` comment
   on issue #807 can activate the existing guarded one-time release job.
   A green PR, branch name or ruleset *proposal* is not a release permit.

The cutover job introduced by #1035 now rejects `protected=false` before
quiescence or mutation. Scientific first-use remains false; paid API calls
remain zero. No new controller, scheduler, queue, source replay, or N Research
executor modification is authorized here.

## Qualification

`go test ./branchpolicy -run TestF139OwnerReleaseRuleset -count=1` checks
the exact JSON file and rejects changed scope, disabled enforcement, bypass,
missing update/deletion rules, unknown rule parameters, duplicate fields and
trailing JSON. It is a source validation **only**, not real enforcement.
