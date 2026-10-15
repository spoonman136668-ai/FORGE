# FORGE R29 — existing isolated Windows runner for real private graph first use

The private `Mind-Palace` repository accepted a source-only one-time hosted test workflow, but GitHub run [#38763588541](https://github.com/spoonman136668-ai/Mind-Palace/actions/runs/38763588541) failed **before recording any executed steps**. The cause is not exposed by available run logs. Do not mislabel that as a passed private export or repeat private hosted minutes without evidence.

R29 uses the already installed **FORGE-CODEX-REMOTE** isolated Windows runner, label `forge-codex-isolated`. This is a one-time branch-specific diagnostic workflow, never scheduled, **with no Codex invocation**, no new runner, no research dispatch and no persistent checkout modification.

It checks out the exact FORGE private-export adapter source via ordinary `actions/checkout` but refuses drift of the pinned file blobs for `mindgraph/export.go`, `mindcontext/reader.go`, `mindcontext/github.go` and the Go CLI. The existing isolated runner's preexisting `gh auth` is required to read `spoonman136668-ai/Mind-Palace` at exactly `5e0e41db5810a0f8296863bac8d636ab961cc35a`; the ephemeral `GITHUB_TOKEN` granted to FORGE is **never** used to attempt private retrieval. No token is pasted into a new GitHub secret, command argument or artifact.

The Go adapter makes only private GitHub GET requests for three allowlisted `.ice` source files, pins the read to a full SHA and returns at most 24 records from global governance and Wingless/Yggdrasil/Research. A new folder in the runner's `RUNNER_TEMP` (not a personal Obsidian vault) contains the derived graph, SHA-256 manifest and linked Markdown notes, all verified, then deleted in a `finally` block. The workflow uploads **no artifacts or private content** and prints only pass/deny markers and bounded counts.

No private data, FSA first-use claim, scientific acceptance, research dispatch, paid model/API, private vault overwrite, account-settings change or additional infrastructure is authorized. Fail closed if isolated runner missing, old authenticated GH access unavailable, source pin changed, or private scratch cleanup fails. Close the diagnostic PR without merging it.

Separate source is already deployed in [FORGE PR #267](https://github.com/spoonman136668-ai/FORGE/pull/267). This workflow only verifies *actual* private first use. It is not a permanent scheduled memory ingestion service.
