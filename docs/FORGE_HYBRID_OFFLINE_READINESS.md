# FORGE Hybrid readiness — offline blocker report, not training

This adds a native Go read-only workflow **diagnostic** after the successful
inactive integration merged in FORGE PR #1567 (main source
`62d729900428cd7686ef828d24a024bd323332b0`).

The historical integration rejected failing Hybrid source heads, but did not
return *which* required CI was missing or failing. This bounded offline command
preserves each observed negative instead of hiding it behind a generic blocked
status. It consumes an operator-supplied GitHub `workflow_runs` JSON snapshot
for the exact private Hybrid repository, filtered to an exact source SHA.

```sh
go run ./cmd/forge-hybrid-readiness -snapshot /absolute/path/hybrid-workflows.json -source-sha <exact-40-character-sha> -experiment G7-S25
```

Read-only output includes the named G4, G5, G7 and experiment-specific run
status, URL, attempt, exact SHA and source-snapshot digest. S24 and S25 reuse
the existing mandatory qualification-workflow names. S26 is *development-only*
and has no execution-admission path; its focused quarter-reserve workflow may
be reported without changing source or granting scientific first-use.

A successful focused workflow cannot mask failed G4/G5/G7. Duplicate
exact-SHA runs are AMBIGUOUS; failed/cancelled runs are nonpass; pending,
missing and stale data remain blocked. Even an all-green caller snapshot has
**no independent source authentication, historical completeness, native
Windows/Linux full regression acceptance, science, first-use, resource
reservation, or execution authority**.

## November 7 checkpoint

- FORGE inactive integration #1567 merged with Linux/Windows/observer PASS.
  This reporter changes no research scheduler, owner, runner, queue, or
  scientific state.
- Hybrid S24 #39 exact SHA `d97c15cf709be63d186adcb58e01e3730cb539e1`:
  focused checks PASS; native runtime regression blocked by missing runtime.
- Hybrid S25 #40 exact SHA `108808f7b685107a76fae1ce5605b7ff9e2bac27`:
  79 focused checks PASS on isolated project runner; required hosted
  G4/G5/G7 failures and full Windows/WSL regression not qualified.
  Negative *untrained* trigger result (no post-switch updates) is preserved
  as a development finding; scientific frozen S25 not run.
- Hybrid S26 #41 exact SHA `ff2667c3eef0bf063ac2681cd03bab9935150c47`:
  development quarter-reserve one-use run
  [#42425731709](https://github.com/spoonman136668-ai/TTT-Hybrid-Lab/actions/runs/42425731709)
  failed at `BLOCKED_RESERVE_GATE_CONTRACT`; its development comparison
  did not execute. That finding is not scientific failure, and S26
  remains independent from S25's frozen protocol.

## Scope

No cross-project credentials, network fetch, new scheduler, new controller,
GPU run, package install, rerun, scientific seed use, or model promotion.
The operator/authorized native Hybrid owner must independently obtain and
authenticate source and original-first-use evidence. This tool only diagnoses
the caller-supplied metadata and never upgrades a blocked candidate.

## November 9 P32 development owner-versus-hosted CI reconciliation

The existing read-only reporter now recognizes `P32-DEV` as a
**development observation only** (not an unattended-execution experiment).
For exact project SHA `7bc49166b83788efc7bfb9da82d39fc420630c46`:

- The existing native project-owner workflow "Native P32-R2 final source actor
  recurrence damage qualification once", run #42548762315, completed SUCCESS.
  Its original-owner log records full Windows/Ubuntu WSL CPU regression before
  589,824 actual original public-source training actions and 6,912 optimizer
  minibatches. This is development evidence, not protected scientific acceptance.
- Hosted G4 run #42548767052, G5 run #42548767056 and G7 run #42548767057
  all report FAILURE on the *same* exact SHA. Their job logs were unavailable
  in this read-only audit, so cause is **UNKNOWN** (not presumptively science
  failure, nor presumptively infrastructure failure).
- In the frozen P32 physical-source comparison, actor-head-only PPO achieved
  200/200 original environment rewards for all three tested seeds; the
  selected-positive seed 4507 fell to 104.125 under full recurrent PPO and
  96.5 under recurrent-only PPO. The strongest conventional two-frame control
  achieved 200/200. P32's broader frozen criterion **did not pass**. These
  are owner-log observations, not a new independent scientific qualification.

The reporter preserves the hosted failures and owner success side-by-side.
A green focused owner run cannot override the failed hosted suite. Even
hypothetically four green observations remain **unauthenticated caller-provided
CI metadata**; source owner, first-use, actual cold checkpoint, runner resource
lease, approved trainer, F139 signed ticket, SQLite migration, release and
scientific acceptance are all **NOT VERIFIED / NOT AUTHORIZED**.
`P32-DEV` is intentionally absent from `requiredHybridWorkflows`, so
the existing inactive assembly cannot admit it. No changes are made to the
existing two-lane controller, scheduled tasks, GPU runner, project repo,
model weights, accepted refs or protected science.
