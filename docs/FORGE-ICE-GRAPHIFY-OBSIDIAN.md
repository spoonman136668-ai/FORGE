# FORGE R17 — ICE / Graphify / Obsidian as the general project structure

**Scope:** the entire FORGE codebase and scientific-program architecture, not just FSA. **Status:** public-safe, derived knowledge layer; no runtime deployment or scientific authority.

## Working structure

- `.ice/manifest.json` declares FORGE's portable knowledge-index contract, safe visibility, exact qualified source ancestry, Graphify 0.9.53 code-only version and output roots.
- `.ice/structure.json` is a typed, cross-linked and source-path-backed map of FORGE components and interfaces: scientific history, Dream-RSI optimizer, prospective logging, FSA review/eligibility/signature/CAS/archive boundaries, hosted simulations, read-only Mind-Palace context, evidence and quarantine, and both Wingless/Yggdrasil lanes. Each node is labeled source-only, design-only or planned.
- `.ice/evidence-index.json` stores **only public engineering qualification pointers** (exact Git commits + hosted run IDs for R1–R16, including negative external-trust evidence) and explicitly preserves not-deployed/not-authorized FSA state. No private experiment results or sealed cohort identities are copied.
- `.ice/derived/graphify/graph.json` and `.ice/derived/obsidian` are **generated** by the existing Graphify CLI and are ignored by Git. Their exact source commit/tree and graph SHA-256 are recorded in `.ice/derived/graphify/build.json`. The user can open the generated folder as an Obsidian vault. This is the same local-code-graph approach already verified in `ckb-knowledge`.
- `iceindex/ice_test.go` validates the machine-readable schema, source-path existence, non-dangling graph links, exact parent identity, no authority uplift, and public-vs-private boundary.

## Build on your existing Windows workstation (when desired)

The script reuses installed Graphify 0.9.53, if present, and otherwise uses a pinned `uvx` package (no model API key). It never alters your existing `ckb-knowledge`, KTRADE or Obsidian vault.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-FORGE-Graphify.ps1
```

The script invokes `graphify extract . --code-only --force` and `graphify export obsidian --graph .ice/derived/graphify/graph.json --dir .ice/derived/obsidian`. A public GitHub-hosted run also attempts the exact same script with pinned `uvx`, after native Linux/Windows regression, generating a public-safe verification artifact. This needs no new cloud account, purchase, token or paid LLM inference. The source graph is derived; the Go source + independently authenticated original evidence remain the source of truth.

## Storage and authority boundaries

ICE is **structured derived knowledge and provenance referencing**, not a new scientific acceptance ledger. Graphify is a source-code relationship extractor; Obsidian is the human navigation layer. None can atomically reserve a first-use cohort, keep a separately held FSA signing key, protect actual original raw results or prove physical rollback resistance.

Private FORGE originals must remain in a *separately qualified FORGE-private archive*. Relevant Mind-Palace private `.ice` is accessed only via the existing pinned, read-only adapter, never mirrored into public FORGE. Scientific records must preserve SUPPORTED, MIXED, NEGATIVE, INVALID and CONSUMED_INDETERMINATE with source lineage; no relabeling or synthetically filling missing outcomes.

**No changes to existing CKB-plane controller, Wingless/Yggdrasil accepted science, KTRADE, broker, runner leases, queues or production.** No new runtime controller, live experiments, accepted-ref mutation or authority promotion. The physical FSA gate [#20](https://github.com/spoonman136668-ai/FORGE/issues/20) and autonomous scientific [#25](https://github.com/spoonman136668-ai/FORGE/issues/25) stay open until independently qualified.

## Reproducibility gate

The R17 workflow requires the exact R16 Git parent/tree, **only the specified additive knowledge files plus a bounded `.gitignore` amendment**, focused ICE tests, one full native Linux and Windows Go regression, vet and build, Linux full race, plus a hosted Graphify 0.9.53 code-only extraction and generated Obsidian vault check. No source semantic changes or additional spending.
