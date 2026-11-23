# FORGE — integrated .ice, Graphify, Obsidian and Mind-Palace context

**Integration source:** historical public architecture work from PR #43 and private read-only export from PR #256. These are **two independent data paths**, sharing conventions and documentation but **never sharing private records or writing authoritative scientific state**.

## Public project architecture: `.ice/` (PR #43)

- `.ice/manifest.json`: advisory knowledge contract; Graphify `graphifyy==0.9.53`, code-only, zero model calls; public graph and Obsidian output locations.
- `.ice/structure.json`: 27 typed architecture nodes and 24 declared links across FORGE research, scientific boundary, provenance, hosted infrastructure, context and Wingless/Yggdrasil. The original R16 map was re-grounded to **existing source paths** on this integration's base; remapped roles are explicitly advisory and do not claim that a particular service is active.
- `.ice/evidence-index.json`: only **historical R1–R16 public engineering qualification references**, not an exhaustive current list, not live scientific status, and not an authority ledger. The original R16 commitment and tree in the manifest document historical provenance **only**, not the current head.
- `tools/Build-FORGE-Graphify.ps1`: opt-in **public code-only** Graphify extraction and separate Obsidian export. Output stays in ignored `.ice/derived/` and `graphify-out/`, away from your existing private Obsidian vault. The tool attempts already-installed Graphify or the pinned `uvx` package. No paid or hosted model use is authorized.

Public example on a machine where Graphify 0.9.53 or `uvx` is installed:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-FORGE-Graphify.ps1
```

Graphify's code map is derived and disposable; Graphify-identified edges **are not science evidence**. This integration does not automatically install external software or send private content to Graphify.

## Private provenance context: read-only Mind-Palace (PR #256)

- `cmd/forge-mind-graph` and `mindgraph/` reuse the current `mindcontext.NewGitHub` and `mindcontext.Reader` read-only adapter, pinned to immutable private source identities.
- A **new**, owner-private output destination **outside the public FORGE worktree** contains `.ice/derived-context-graph.json`, SHA-256 evidence manifest, an Obsidian-ready `obsidian/` vault, and optional `graphify-input/` Markdown corpus. Records explicitly carry project, record identity, source references and extracted relationship origin. No invented relationships or evidence-status upgrades.
- Text from Mind-Palace is untrusted: HTML and Obsidian wikilink syntax are escaped. Private records must **never** enter a public CI artifact, `.ice/structure.json`, `graphify-out/`, or FORGE Git history. Do not merge private and public vaults.
- The PowerShell wrapper requires an independently scoped, fine-grained private **read-only** token and refuses an existing output vault. It does **not** launch Graphify by default. External semantic Graphify analysis requires separate explicit backend/privacy permission, and must not use a paid service or expose private data by default.

Private example **only from an appropriately authorized private host**:

```powershell
.\scripts\forge-mind-private-graph.ps1 -PrivateOutput 'C:\FORGE-Private\mind-graph-new-run'
```

Do not paste any private credentials into GitHub, the public CI or messages. Installing this source **does not mean** private Mind-Palace credentials/connectivity or a completed private export have been qualified. Public CI exercises synthetic input only.

## Authority and scope

GitHub source, independently verified raw scientific originals, and the existing FSA controls remain authoritative. Neither `.ice`, Graphify, Obsidian, nor the Mind-Palace adapter can issue a first-use claim, consume a scientific cohort, merge an approved PR, dispatch a research experiment, change the FORGE budget, override the source auditor, or operate KTRADE/CKB-plane. Existing Wingless and Yggdrasil lanes remain independent.

No new controller, scheduled task, paid model/API, Cloudflare deployment, user-setting change, or Mind-Palace memory-writing service is created.

## Qualification

The integration CI runs source-grounded `iceindex` and synthetic `mindgraph`/Mind-Palace tests, a full fresh Go suite, vet, build, Linux race and native Windows PowerShell parse. A later **explicit opt-in** public code-only Graphify extraction can qualify the generated Obsidian artifacts with `graphifyy==0.9.53`; that optional third-party execution is **not** a prerequisite for safe read-only core integration. Live private export also requires a separately authorized private-runner first-use qualification and is intentionally **not** part of public CI.
