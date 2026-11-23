# MP-AI05 — one-shot read-only consumer operating boundary

**Status:** Authorized one-shot consumption proven on the original isolated FORGE Windows runner. This is **not** a running service, autonomous controller, global activation, model learning, or scientific acceptance.

## What was qualified
- [Pinned operational Windows run #40481979329](https://github.com/spoonman136668-ai/FORGE/actions/runs/40481979329) on `FORGE-CODEX-REMOTE`.
- Source commit: `7ad7230a82e3c748aa5336b7288ad2b45d42630c`.
- The actual `tools/mpai05_recall_cli.py` consumed a private read-only Mind-Palace checkout, with the same query in **off**, **shadow**, and **eligible** modes.
- Receipts: off = disabled / 2 matches; shadow = disabled / 2 matches, identical private result digest; eligible = normalized / 2 matches; source identity and original `source_refs` verified. Temporary result files removed after execution.
- [Focused CI #40482118919](https://github.com/spoonman136668-ai/FORGE/actions/runs/40482118919): 9 one-shot and 8 existing normalizer tests passed.
- There was **no difference in top-four returned record IDs for this particular operational query**. Do not claim improved answer quality from it.

## Invocation boundary
The tool is a **single invocation**, not a background job. An authorized caller provides an absolute path to an already cloned and pinned Mind-Palace checkout, its 40-character Git commit, a private absolute output-file path outside either Git worktree, and a query over **stdin** (never a process argument). The client reads only the `Mind-Palace` project, invokes the existing source-verifying `MemorySnapshot`, and writes the private result to a *new* file (exclusive create). It logs only mode, routing, record count, SHA pin and a non-content shadow-change indicator.

Modes:
- `off` (default): identical original retrieval; immediate rollback.
- `shadow`: serves the original result; compares a normalized candidate but **does not serve it**.
- `eligible`: serves normalized context only for the two prequalified exact query templates; unfamiliar queries pass through and empty normalized results fall back to the original query.

The trusted caller owns temporary private file permissions and deletion. No scheduler, extra controller, paid model/API, autonomous activation or credentials are introduced. The fixed GitHub Actions entrypoint uses an authorized runner, static non-sensitive query, and cleanup; it is a bounded operational demonstration, not live ChatGPT traffic. No protected scientific holdouts are accessed.

## Release boundary
Merging the CLI makes the one-shot opt-in available, **not globally active**. A real application must explicitly invoke it with mode `eligible`. Do not patch F139's Go `mindcontext.Reader.Read` because it selects projects, not free-form text queries. Promote only after observing authorized real consumer traffic with non-content telemetry and a meaningful independent answer-quality comparator.
