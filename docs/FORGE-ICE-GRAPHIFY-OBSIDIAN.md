# FORGE private .ice → provenance graph → Obsidian + optional Graphify

Purpose: reuse the existing read-only, source-pinned Mind-Palace .ice adapter without another controller, memory-writer, scientific authority, schedule, cloud bill or API.

## Implementation

1. The FORGE-private runtime supplies FORGE_MIND_PALACE_READ_TOKEN, a fine-grained token restricted to Mind-Palace Contents:read. Token bytes are never command arguments, logs or public Actions secrets.
2. cmd/forge-mind-graph uses the existing mindcontext.Reader and NewGitHub to read .ice/remote-bootstrap.json, .ice/remote-catalog.json and .ice/remote-index.ndjson at one immutable SHA. Wingless, Yggdrasil, Research and global governance are allowed; KTRADE and CKB-plane are excluded.
3. mindgraph.Build constructs only explicitly supported edges: record → project and record → source reference, each marked EXTRACTED with an original record identity. No fabricated relations, accepted scientific evidence or research directives.
4. mindgraph.WriteNew creates an entirely NEW, private (0700 directories; 0600 files) destination outside the public FORGE checkout. It refuses an existing vault and never writes back to Mind-Palace.
5. Output: .ice/derived-context-graph.json, .ice/derived-export-manifest.json with SHA-256s, an Obsidian-ready obsidian/ vault with project/record/source links, and graphify-input/ markdown notes. Advisory text is escaped to block untrusted Obsidian wikilink/HTML injection.

## Minimal Windows use

Open PowerShell in FORGE. Provide a fine-grained private read-only token via your separately controlled secret store (never paste credentials into a public repository). Choose a new folder under an existing private parent, e.g. C:\FORGE-Private\mind-graph-new-run.

    .\scripts\forge-mind-private-graph.ps1 -PrivateOutput 'C:\FORGE-Private\mind-graph-new-run'

Then open the generated obsidian/ folder as a vault in Obsidian. The Obsidian-ready native export needs no plugin, external service or API token.

## Graphify

The intended optional graph engine is the open-source Graphify-Labs/graphify CLI; its official PyPI package is graphifyy (double-y). graphify-input/ is suitable for a private Graphify semantic scan. It is NOT a Graphify-native graph.json file; the derived .ice graph is a separately labeled FORGE provenance projection.

Graphify can analyze Markdown via a model backend, which may send private bytes to an external provider or incur paid API usage. FORGE does not install or invoke Graphify by default. If you already installed Graphify and have consciously configured a safe private/local backend, the PowerShell -RunGraphify -ExplicitlyAllowExternalSemanticAnalysis switches build a separate graphify-obsidian/ export. The wrapper clears the Mind-Palace token before invoking third-party code and never overwrites an existing personal Obsidian vault.

## Scientific and operational boundaries

The generated graph and notes are advisory, never independent FSA scientific acceptance. Sources must still be independently verified before qualifying science. Any Graphify INFERRED edge remains hypothesis-only.

This adapter cannot ingest/update curated Mind-Palace .ice records, dispatch an experiment, change a budget, start a controller or background process, or share FORGE/KTRADE credentials. Current R12 research CI continues independently. No actual private GitHub token is placed on public CI; qualification uses only synthetic input.

Before claiming live always-on memory, a separately configured private runtime must demonstrate actual authenticated connectivity, safe output custody, token revocation and bounded records. No extra scheduler, FSA service or paid API is required for the qualified local export.

Acceptance: full Linux and Windows FORGE Go regression, focused mindcontext/mindgraph tests, new-output and injection negatives, and all four Windows binary builds. Optional external Graphify execution is NOT part of public CI.
