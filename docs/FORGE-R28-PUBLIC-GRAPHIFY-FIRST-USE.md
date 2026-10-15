# FORGE R28 — actual public Graphify/Obsidian first use

This temporary source-pinned GitHub Actions qualification **runs** the already-integrated `tools/Build-FORGE-Graphify.ps1` on current public FORGE code at Graphify `graphifyy==0.9.53` with `--code-only` and zero model/API credentials. It does not access or export private Mind-Palace data.

It requires a real generated `.ice/derived/graphify/graph.json`, a separate Obsidian Markdown vault, a SHA-256-identical public `build.json`, exact git commit/tree identities, zero scientific authority and a clean git worktree. It retains public-only output for seven days, not a durable scientific original.

This workflow is a one-time diagnostic on `engineering/forge-r28-public-code-graph-first-use-20261015`. **Do not merge the workflow or introduce a new controller** solely for this check. Close the diagnostic PR after authentic validation; the real export capability is already on `main`. Private Mind-Palace first use stays separate, never triggered with a public GitHub token, never paid.
