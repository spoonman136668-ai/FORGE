# F139 V18 — enforce immutable owner-release refs

**Status:** administrator-ready proposal; **not installed**. This document does
not grant source, model, worker, or scientific execution authority.

## Verified original state (2026-10-28)

- Original deployed F139 V17 and protected `main`:
  `3775bed30891ff748197a539afe5b92813680e26`.
- The complete V18 original-owner release workflow in draft FORGE #1035,
  commit `5a040dd4dd8c4a3203c7e4d751a0cf01065717ad`,
  passed all three exact-head controller/public/hosted Linux/Windows workflows.
- A **pre-merge candidate only**
  `f139-owner-release-5a040dd4dd8c4a3203c7e4d751a0cf01065717ad`
  matches the PR HEAD, but GitHub reports `protected=false`. It **must not**
  be used as the final owner-release reference.
- The active main-only ruleset `25031517` requires PRs and permits **only**
  the `merge` method. A PR #1035 merge therefore creates a **new merge
  commit M**, rather than advancing main to that PR's head. Consequently the
  final release ref must be **created after the merge**, at the actual main
  SHA M, never from any already created PR-head preview ref.
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
administrator with **Administration:write** can use the checked-in, bounded
PowerShell handoff from a qualified, clean checkout of this governance branch,
under their own already authenticated GitHub CLI session:

```powershell
# Read-only by default: check original V17 main, issue #807, source branch,
# negative ruleset tests and whether the admin lock already exists.
pwsh -NoProfile -File scripts/Install-F139V18ReleaseRuleset.ps1

# One-time bounded admin write, only after authorizing the reviewed ruleset:
pwsh -NoProfile -File scripts/Install-F139V18ReleaseRuleset.ps1 -Apply
```

The script refuses any changed main SHA, owner-policy drift, dirty/unqualified
checkout, missing active main ruleset, ambiguous duplicate release rules,
or weakened scoped source policy. It uses exactly one GitHub administration
POST when the rule is missing and `-Apply` is explicitly provided; otherwise
it remains read-only. Afterwards it independently reads the actual ruleset
detail and the exact pre-merge preview branch's `protected` value. Any 403
or insufficient admin permission fails closed. It **never** merges, creates
a final release ref, dispatches a workflow, stops the original owner task,
or changes the F139 SQLite ledger.

Run the command from a clean checkout of the **qualified governance proposal**,
not from the live Windows F139 controller's installed source directory.
Do **not** create a duplicate if a matching rule already exists; reconcile it
instead. Never put tokens into chat, files, workflows or issue comments.

### Independent verification before any owner-cutover event

1. Query `GET /repos/spoonman136668-ai/FORGE/rulesets` and the new ruleset
   detail: enforcement must be **active**, target **branch**, include exactly
   `refs/heads/f139-owner-release-*`, have **zero** bypass actors, and require
   both `update` and `deletion` restrictions.
2. Verify the existing main ruleset `25031517` remains active and
   limited to `refs/heads/main`. Verify the release-ref ruleset makes the
   existing PR-head preview branch report `protected=true`; this proves
   applicability **only**, not that the preview SHA is a releasable target.
3. Independently observe a GitHub-denied update on a dedicated **disposable
   test** ref of the same release pattern, if a safe admin test is available.
   Do not mutate or delete a genuine release ref. The authoritative
   production source pin remains the old V17 main until a merge.
4. Recheck original Windows owner read-only and protected V17 main, plus
   issue #807's source pin, event chain, ledger integrity, no READY/active
   tasks and no spent free-model replay. **Do not merge while blocked.**
5. Merge the fully qualified combined #1035 into protected `main` **only
   after** independent original-owner release approval, validated enforcement,
   and a guarded, ready-to-execute cutover. The permitted `merge` method
   creates a **new** main SHA M that is different from the PR head.
   Confirm the actual protected main M has the exact reviewed V18 source
   and workflow, and obtain successful fresh `linux` and `windows`
   qualifications **for M** (plus all independently required owner gates).
6. Create **one** `f139-owner-release-M` branch from the observed, newly
   protected main SHA M; independently read back its exact SHA,
   `protected=true`, the active no-bypass update/deletion ruleset, and
   the unchanged original V17 installation and owner policy. Never move
   any existing preview branch, and never substitute a pre-merge PR SHA.
7. Only then may an authorized original owner post the exact
   `F139-V18-OWNER-CUTOVER M` event on issue #807. The existing original
   owner workflow checks M against both protected main and this immutable
   release branch **before stopping the task**, then backs up and attempts
   a single original ledger transition. A passing PR, approved ruleset
   *proposal*, or earlier preview ref is not release authorization.

The cutover job introduced by #1035 now rejects `protected=false` before
quiescence or mutation. Scientific first-use remains false; paid API calls
remain zero. No new controller, scheduler, queue, source replay, or N Research
executor modification is authorized here.

## Qualification

`go test ./branchpolicy -run TestF139OwnerReleaseRuleset -count=1` checks
the exact JSON file and rejects changed scope, disabled enforcement, bypass,
missing update/deletion rules, unknown rule parameters, duplicate fields and
trailing JSON. It is a source validation **only**, not real enforcement.
