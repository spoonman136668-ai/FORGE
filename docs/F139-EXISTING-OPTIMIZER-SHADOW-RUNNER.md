# Existing five-optimizer shadow runner

This integrates the pre-existing, read-only five-optimizer runner from FORGE PR #233, exact source `73e65a22e9fd8602fcb1118ad54a5cf3cec32e27`, onto current main. It does not install that source into the active F139 owner, change policy #807, pause its task, or modify its original ledger/worker release ref.

## What actually executes

With complete independently sourced evidence and pins, `cmd/forge-optimizer-shadow` calls the existing Dream-RSI, Shinka/Pareto, ThetaEvolve, Promptbreeder and GenEnv libraries through the existing `optimizerbridge.EvaluatePinnedExportWithAudits` entry point. This is bounded historical/advisory computation only. It does not publish source candidates, dispatch experiments, promote policies, admit scientific first-use, or claim future improvement.

The live V33 owner remains separately pinned to `b8d571763e6035b6c7cc602de8c562449142c573`. Its native generation/evaluation/custody loop continues independently. Its development PASS records are not automatically independently accepted scientific outcomes, randomized policy histories, or authority for Theta training/policy activation.

## Required real inputs

The runner requires all eight separate absolute file paths:

| Flag | Required input |
|---|---|
| `--wingless-evidence` | Original source-bound Wingless lane evidence |
| `--yggdrasil-evidence` | Separate original Yggdrasil lane evidence |
| `--signed-export` | Existing custodian's signed immutable export manifest |
| `--independent-anchor` | Independently supplied public custody identity and monotonic/source-birth pins |
| `--independent-lane-pins` | Independently supplied frozen optimizer/history public pins |
| `--wingless-selection-audit` | Source-linked, independently signed Wingless decision-time assignment audit |
| `--yggdrasil-selection-audit` | Separate Yggdrasil assignment audit |
| `--independent-audit-pins` | Independently supplied public auditor identities |

Use only the existing approved exporter/custodian and qualified execution route. Do not generate replacement trust anchors, sign fabricated histories, backfill missing decision-time menus/propensities, request private keys, or convert native V33 outcomes into accepted scientific training evidence. The source API validates consistency with supplied pins; real independence and operational custody still require external qualification. No authenticated live input bundle is supplied by this source adoption.

On an already authorized qualification/research checkout, the existing entry point is `go run ./cmd/forge-optimizer-shadow` with all eight flags above. Missing, aliased, malformed, mismatched or unsigned inputs fail closed; no optimizer report or partial plan is emitted. The command performs local bounded file reads and stdout reporting; it makes no network requests, mutates no existing data, and starts no controller. Protect the resulting report through the existing evidence custody process.

## Scientific and optimizer boundaries

Dream-RSI policy optimization requires authenticated original chronological histories and valid frozen disjoint train/validation contracts. An observed historical policy trace is not audited randomized evidence. Shinka/Pareto reports historical diversity and screen scores, not prospective gains. Theta produces a bounded train-only parameter proposal from supplied qualified training inputs; the separate accepted-outcome/activation gates remain mandatory for any operational use. Promptbreeder/GenEnv results remain untested proposals until the existing independent source/evaluation boundaries accept them.

The signed export and selection-audit checks do not establish authentic randomization, independently operated key custody, complete real first-use reconciliation or scientific acceptance merely because signatures parse. FSA #83 and Dream-RSI #25 are preserved. The running owner is not reconfigured to consume shadow recommendations by this change.

## Exact reused source

Every code/test blob below is copied by Git object identity from the pinned existing PR; no replacement optimizer is implemented.

| Path | Original Git blob |
|---|---|
| `optimizerbridge/bridge.go` | `04e275423fc44d86b31d2fa210ae8e285bf52faa` |
| `optimizerbridge/bridge_test.go` | `66cc82d369a8e75e4bd5ca90f7b3656dcffba22e` |
| `optimizerbridge/custody.go` | `5687432a6bb41eb0fa6ce0e6945c90f3a2e467a7` |
| `optimizerbridge/custody_test.go` | `1a7270ad2b68a40451208782eafc765d6543f2b5` |
| `optimizerbridge/selection_audit.go` | `48810d9935b0cfd119991b22300cbaa783bd9adb` |
| `optimizerbridge/selection_audit_test.go` | `bca3b3c4c549c81f68e35900f57c497f6ad73192` |
| `optimizerbridge/admission.go` | `fd0ba2533a65d464ef6e78b3970996d1a0b224b0` |
| `optimizerbridge/admission_test.go` | `d7764c3d776b8ed5396b524f7dea7d16346497d2` |
| `cmd/forge-optimizer-shadow/main.go` | `628c17cc890433f3e12953bf327ec4a132599d37` |
| `cmd/forge-optimizer-shadow/main_test.go` | `f08777a2b45bf368119db806b7aa6e45399c059f` |

The original #233 Cloudflare provisioning/migration workflow, older controller/execution paths, private secrets bindings and source-activation machinery are excluded.

## Qualification

Mandatory current-source Linux and Windows full regression, Go vet/build and Linux race/isolation checks are required before integration. The adopted tests execute all five actual packages using explicitly synthetic signed fixtures, preserve negatives and invalid history, reject lane/source/receipt reuse and missing/tampered trust, and verify that no authority is granted. Synthetic qualification does not establish operational data availability or live optimizer use. The active release continuity is independently verified through the existing immutable release-pin mechanism after any main merge.
