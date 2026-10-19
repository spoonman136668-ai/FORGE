# G61 — FORGE source coverage by exact immutable identity

Status: **engineering candidate; qualification required before integration**. No scientific admission, deployment, runtime launch, controller action, or research execution authority is granted.

## Scope lock

- Historical G29 atlas source: `c6f5823ee48c1df81d6d197b7cff3090b392c4cb`.
- Required committed G29 atlas Git blob: `0030963a413ff9905138fc9bb25d169199658166`. The original committed G29 JSON, HTML and ICE remain untouched.
- G60 target source: `30a29c80326cc7e39470c90e63af72dc1b9811b5`.
- Expected unchanged content-addressed source records: **747**.
- Expected modified indexable paths: **16**; newly indexable paths: **18** (including one C# file). Total bounded delta: **34**.
- Expected resulting advisory source inventory: **781** files.
- G61 engineering branch may change only `cmd/forge-code-atlas/{main.go,g61.go,g61_test.go}`, the existing G29 qualification workflow and this document.
- Changes to FORGE `main` *after* the G60 target require an explicit source-and-interface reconciliation before merging. Never silently incorporate their new files into these counts.

## Confidence and navigation

Unchanged locators are reused only with exact Git blob identity and the original pinned G29 artifact. Only changed/new paths are parsed. Go definitions use the native Go AST parser; Python/PowerShell/workflow names use lexical locators. The previously uncovered `scripts/F139WindowsJobSupervisor.cs` receives **C# lexical class/struct/interface/record declaration locators**, not C# compiler-resolved calls. No candidate link is promoted to a compiler-verified or runtime relationship. Unknown and dynamically dispatched calls remain unverified.

A complete, searchable, static HTML navigator is assembled from the reused baseline and bounded delta in the hosted runner's temporary directory; the detailed JSON, HTML, ICE and provenance report remain runner-private and are not uploaded as source evidence.

## Qualification

Existing GitHub-hosted G29 Windows/Linux workflow runs focused Go tests, `go vet`, exact baseline/target/delta reconciliation, source-pinned C# and Go locator assertions, and offline HTML generation. FORGE's existing protected-branch regression workflow supplies its already-required complete repository test/build boundary; no separate regression loop or controller is created.

The generator stops on missing or altered baseline artifact, dirty worktree, nonancestor target, unrelated candidate change, original-source deletion, unexpected file-count/scope increase, or mismatched Git blob. A PR and passing checks do not by themselves authorize protected-branch merge or change scientific acceptance.
