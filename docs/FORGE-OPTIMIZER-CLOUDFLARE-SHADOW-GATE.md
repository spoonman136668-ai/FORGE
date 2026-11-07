# FORGE optimizer integration: existing Cloudflare, no new controller

**Stage:** source-only, read-only dual-lane qualification. NOT real policy promotion.

The existing FORGE research worker/controller remains the only research orchestrator. Cloudflare is **the user's pre-existing durable evidence/custody infrastructure**, not a replacement orchestrator or a reason to build another FSA cluster. This change provisions no Cloudflare accounts, buckets, credentials, worker service, new cron, or scientific first-use authority. No GitHub Actions secret is read.

The shared `optimizerbridge` composes existing `dreamrsi`, `evoportfolio` R8 Pareto, `promptlineage`, `thetaadapt`, and `genenv` under separately provided exact evidence/source pins. It refuses missing/nonmatching trust roots; fails atomically across Wingless and Yggdrasil; retains negative/mixed/invalid/consumed evidence, per-family diversity, frozen budgets, training-only proposals and `UNTESTED` labels. It issues **no execution claims**.

## Fit to existing Cloudflare

Do not invent Cloudflare account IDs, bucket names, R2 endpoints, namespaces or signer keys. The existing authorized evidence ingestion path can *supply* to the read-only bridge: (1) immutable evidence and train/validation manifests retrieved from the existing private Cloudflare store; (2) their SHA-256s + verification key(s) from an independently held/pinned trust source, not inferred from the retrieved objects; and (3) separate Wingless and Yggdrasil frozen portfolio, generator plans, compute caps and first-use high-water. The output is a content-addressed shadow selection comparison; the existing authorized retention pathway may replicate it back to Cloudflare with immutable object naming and original-source metadata.

**Never treat R2 object existence, bucket operator ownership, an ETag or a key name as independent signing, immutable retention, CAS, FSA control, or proof that experiments were randomly assigned.** Ed25519 history signatures and independently pinned source hashes must verify. For causal improvement, Dream-RSI demands genuine audited randomized logging probabilities and prospectively qualified independent evaluation. Ordinary GitHub experimental result histories are observational and do not qualify causal counterfactual improvements. Cloudflare billing/usage caps remain governed by the existing user setup; no new continuous polling or bulk duplication is activated by this source gate.

## Honest operational gates

1. Source-only merged/qualified five-enhancement shadow composition via synthetic signed histories; no original science.
2. Bind read-only Cloudflare-backed **authentic** evidence manifests through the already-authorized worker; require independent original byte digest and verified remote retention, full consumed-first-use reconciliation, accurate propensity audit. If incomplete, output `NOT_QUALIFIED`, not an optimizer recommendation.
3. Compare frozen optimizer proposals versus existing selection on **prospective**, distinct science, under exact per-lane compute budget. No sealed first-use without existing authority. Require meaningful advantage and negative controls before promoting any optimizer.

No FORGE engineering R32/R33 modification, duplicate research controller, Cloudflare provisioning, paid API or KTRADE changes. F3 stays `NOT_ADMITTED`. Research can continue independently while this bridge is qualified.


## Implemented source-only read-only export seam (stage 2 preparation)

`optimizerbridge.EvaluatePinnedExport` and `cmd/forge-optimizer-shadow` now accept canonical, immutable **already-exported** Wingless/Yggdrasil evidence JSON supplied by the **existing** authorized Cloudflare evidence worker. No endpoint/account/bucket/namespace is invented or accessed by this source patch. The CLI reads five separate **absolute regular-file** inputs:

```text
forge-optimizer-shadow \
  --wingless-evidence ABSOLUTE_PATH/w.json \
  --yggdrasil-evidence ABSOLUTE_PATH/y.json \
  --signed-export ABSOLUTE_PATH/export.json \
  --independent-anchor ABSOLUTE_PATH/anchor.json \
  --independent-lane-pins ABSOLUTE_PATH/pins.json
```

The first two files are canonical serialized `optimizerbridge.LaneEvidence` objects; the third is `optimizerbridge.SignedExport` with two immutable object-key/digest/first-use/source-birth observations. The last two files MUST come from independent trusted pins outside the Cloudflare export and outside the FORGE working repository; they correspond to `optimizerbridge.ExternalTrust` and `[]optimizerbridge.LanePins`. Sign the canonical JSON serialization of `SignedExport.Manifest` using a separately held custodian Ed25519 key with signature domain `FORGE-OPTIMIZER-CLOUD-EVIDENCE-V1\\x00`. Never provide private signer keys to the FORGE runner.

The verifier enforces exact bytes, detached signed manifest digest and trust key, monotonic minimum revision, distinct lane evidence/keys/source-birth ledgers/consumed-first-use ledgers, independently pinned first-use high-waters, and all five existing signed-history and frozen-budget gates. Export evidence from a genuinely independent worker and preserve original negative/invalid histories. A signature that was generated by this CI or derived from the fetched object is **not independent source custody**.

**Current operational truth:** Neither the export files nor separately held real pins have been provided to this source branch. FORGE's existing GitHub archive manifests enumerate byte-verified originals but do not furnish the independently audited randomized Dream-RSI histories or complete first-use ledger required to run this gate on authentic science. Consequently no authentic Cloudflare read, zero accepted prospective comparisons, zero optimization-authorized science, and no live successor claim can be made from these tests. The CLI emits no advisory if any input is incomplete. Its successful result always marks remote operational custody, complete first-use reconciliation, scientific improvement and dispatch authorization **false**. Genuine operational proof must be attached from the pre-existing worker by its legitimate owner and separately verified before any further gate.

**Usage cap:** Manual/event-triggered invocation only on an existing evidence batch. No polling, new Cloudflare bucket, Worker, scheduled task, automatic replication or paid API. Never store sealed histories, private trust anchors, credentials or raw private evidence in public CI logs/artifacts.

## New bounded qualification: independently signed selection-claim audit

The read-only CLI now additionally requires `--wingless-selection-audit`, `--yggdrasil-selection-audit`, and `--independent-audit-pins` from the **same existing independent custody/review pathway**. It refuses a successful report if the evidence is not independently signed or if signed randomization claims, first-use receipts, logged probabilities, source history, or assignment-event identifiers disagree. These are separate per-lane inputs and do not create a new signer, controller or service.

This additional review verifies **claim consistency**, not actual randomized assignment. An Ed25519 attestation of a claimed probability, or an event digest lacking independently validated source bytes and timing, does not establish randomized logging or unbiased causal estimates. Output therefore always retains `actual_randomization_independently_demonstrated=false`, `scientific_improvement_established=false`, and `prospective_science_authorized=false`. An authentic operational custodian must confirm the actual selection process, source-birth time, independent event custody and propensity-generating mechanism before prospective comparison. If those are unavailable, do not promote selection or invent a shadow improvement.

The external files are supplied exclusively to the existing worker. No live Cloudflare read occurs in public CI; no secret, private evidence, protected cohort, or signing key is published.


## Next gate — mandatory dual-lane signed-assignment shadow admission

The read-only `forge-optimizer-shadow` CLI **requires** three additional absolute regular-file inputs: `--wingless-selection-audit` (canonical `SignedSelectionAudit` JSON), `--yggdrasil-selection-audit` (canonical `SignedSelectionAudit` JSON), and `--independent-audit-pins` (a two-element array of separately supplied `SelectionAuditPin`, Wingless then Yggdrasil). Existing five inputs remain required. Use only an existing authorized worker's previously exported genuine records and independent auditor pins. No additional scheduler, Cloudflare reads, uploads, original dispatch, or secrets are created by this gate.

`EvaluatePinnedExportWithAudits` first verifies the independently signed immutable export and all five optimizers, then validates both complete original selection-audit histories, with distinct signing identities across custodian, history signers, and auditors; mismatching/duplicated assignment and source receipts fail **atomically**. Its historical baseline/Pareto comparison reports **screening scores, overlapping finalists, and reserved compute only**. This is a descriptive frozen-history comparison, **not** observed future performance, causal proof, scientific acceptance, or permission to promote. Both genuine independently audited randomized assignment and prospective outcomes on new, disjoint original cohorts remain separate external scientific qualification gates. Existing GitHub historical artifacts must never be backfilled with invented assignment events/propensities. The CLI fails closed if existing Cloudflare evidence lacks any required audit. PR stays draft until authentic evidence arrives and prospective selection comparison independently qualifies.

## Audit-first integration fast path (R11)

The exported bytes must first pass exact manifest signature, content identity, independently pinned source-birth and consumed-first-use high-water checks. **Both** signed assignment audits must then pass complete identity/reuse checks before historical Dream-RSI/Pareto/Promptbreeder/Theta/GenEnv replay begins. A bad audit therefore consumes **no optimizer compute** and produces no partial report. On accepted immutable inputs the five methods run only once; compute is not wasted on unauthenticated evidence. The independent FSA, genuine physical Cloudflare readback, authentic randomized assignment, prospective improvement, sealed first-use, and live selection **remain unqualified** unless separately demonstrated. No new Cloudflare resources or credentials are used.

## Existing Cloudflare service correction — October 14

Operator-established setup is **Cloudflare Workers with SQLite-backed Durable Objects** (account ID + account-owned Workers Admin API token in existing GitHub secrets). It is **not** established as an R2 bucket. References above to an already-existing R2 evidence bucket are historical design assumptions, **not a verified deployment**; do not provision R2 or treat a missing bucket/403 R2 permission as a defect. For optimization evidence, do not assume a Worker or Durable Object instance already holds signed scientific records.

Read-only GitHub-hosted probe authenticates the account-owned token via `GET /accounts/{account_id}/tokens/verify`, then inspects existing Workers script metadata and Durable Object namespaces via GET only. It does **not** instantiate DOs or access any sealed research data. This is account/control-plane connectivity only; independent scientific custody, exact source and first-use high-waters, real replay evidence and prospective optimizer effectiveness remain **NOT QUALIFIED**. It does not create new Cloudflare resources or another FSA/controller. Existing science continues.


## R15 — Reuse current D1 with a bounded append-only original archive contract

The operator's existing Cloudflare Worker and existing D1 database are now independently identity-matched by the current 100%-traffic script version; two fixed SELECT-only SQLite metadata inspections proved **one existing table with no recognizable source/custody columns**. This does **not** prove that table is empty, disposable, or suitable for original science. Preserve it unchanged.

`d1retention/schema.sql` is a **separate proposed additive-only candidate** for the **same existing D1 database** (three content-addressed original/chunk/seal tables plus immutable update/delete guards and partial-seal rejection). The candidate is installed and tested only in a fresh local in-memory SQLite database under GitHub Actions. It is **not** run against Cloudflare. The database remains D1 Read only; no token promotion to Write is needed for this source gate. At most 4 MiB per original ZIP, split into at most 64 chunks of 64 KiB, retaining each project's distinct original IDs, run/artifact/source identities, source manifest digest, byte length and explicit `UNQUALIFIED` status. A submitted seal is only a structural claim; the future exporter MUST independently reassemble bytes, rehash every chunk and entire ZIP, verify source-birth/first-use and independent signatures, and separately prove off-site retention. D1's table immutability triggers do **not** constitute a physically independent external trust authority or tamper-proof database snapshot.

Before any live migration: inspect schema namespace collisions and database backup/restore; freeze exact SQL digest and expected head, qualify D1 deployment privileges separately, and require the operator's legitimate deployment process to apply a bounded additive transaction. Before any live evidence write: verify genuine previously archived original bytes and separate signed custody/first-use pins (no synthetic substitute), enforce cross-lane and once-only replay boundaries, and never reuse consumed originals to generate new experiments. No public GitHub artifact may carry private source evidence or secrets. The optimization bridge remains **shadow advisory**, with no first-use/dispatch or retrospective causal improvement claim.


## R15 read-only byte restoration qualification

`d1retention/restore.py` requires a fully specified **independently supplied** immutable research-original identity pin. It reads a sealed original plus at most 64 pre-existing chunks from a SQLite connection; it rechecks lane/repository/run/artifact/source identities, bounds, ordered chunk positions, each SHA-256 and the concatenated original SHA-256. Missing seals, forged chunk hashes, inconsistent source identities and corrupted payloads fail closed. Its report deliberately always leaves `independent_source_custody_verified`, `first_use_reconciled`, `scientific_accepted` and `dispatch_authorized` false. A pin derived from the D1 database itself does not qualify as independent. The tests run against **in-memory** SQLite only, with no writes to Cloudflare, no real original bytes imported and no original science executed. Offline byte reconstruction is not proof of retention across GitHub expiration or remote failure.

## R16 — exact-source D1 migration preflight (not a production migration)

`d1retention/migration.py` is an **offline-only** fail-closed simulation. It operates on an in-memory SQLite connection, requires exact pinned SHA-256 digests of both the proposed `schema.sql` and pre-existing non-FORGE schema, rejects any `forge_research_*` table/index/trigger/view collision (including partial installation), refuses file-backed databases and active transactions, runs the proposed additive DDL inside an explicit transaction, and validates the existing schema is preserved with exactly 3 archival tables and 8 triggers. Negative tests cover wrong pins, schema drift, partial install, duplicate install, unexpected objects, file-backed connections and rollback of a partial DDL failure. None of these tests provides independent operational custody.

The existing one-shot Cloudflare read-only probe checks the current fully serving Worker version and exact `forge` D1 binding against independently listed D1 database metadata. It now also issues **one additional bounded, SELECT-only namespace-collision query** on `sqlite_master`; only the number of reserved objects is reported, not their names or any stored research/user records. A successful result means **eligible for a migration review**, never that a migration ran. The actual D1 database remains **unchanged**.

**Remaining live gate:** authorized backup/restore, verified unchanged schema source and cloud database identity, scoped one-time schema installation through the existing legitimate Cloudflare administrative channel, and a fresh read-only post-install audit. Do not elevate the public GitHub CI token to D1 Write or use an unprotected Worker endpoint. After installation, original byte ingestion still needs source-pinned independent provenance and sealed first-use reconciliation before it can count as scientific evidence. No duplicate research controller, paid API or alteration to independent Wingless/Yggdrasil experiments.

## R17 — D1 native Time Travel recovery bookmark, read-only qualification

Cloudflare D1 production databases use built-in Time Travel. The currently documented availability is 7 days on the Free plan and 30 days on Paid; bookmarks eventually expire. A bookmark is a **candidate recovery point**, not a verified restore. Never place raw bookmarks, account identifiers, tokens or scientific evidence in public GitHub logs/artifacts.

The GitHub-hosted read-only D1 probe now verifies exactly the bound live database identity, fetches its database backend version with a GET, then retrieves its **current Time Travel bookmark with one GET only** if the version is `production`. It emits only presence/qualified status, never the bookmark itself. The local `d1retention/recovery.py` verifies the provider response shape and deliberately records `restore_attempted=false`, `full_backup_restore_qualified=false`, `live_schema_install_approved=false`. If the backend is not `production` or permission is denied, this stage remains blocked. This workflow never exports a database, changes D1 permissions, calls the restore endpoint, or installs archive schema.

A live restore would **overwrite the database** and cannot be conducted as an automated public CI acceptance; require separate operator authority, interruption window and reversible evidence. The migration remains uninstalled while the one-time bookmark check qualifies.

## R18 — explicit operator-only one-shot D1 archive installer

\`d1retention/install_remote.py\` binds the CURRENT 100% serving \`curly-hat-6a9e\` Worker version, its EXACT \`forge\` D1 binding, independent account D1 listing and the production backend. It refuses ANY pre-existing \`forge_research_*\` object. It reads the current Time Travel bookmark, validates source HEAD + exact SHA-256 of \`d1retention/schema.sql\`, parses all 11 SQL statements while preserving trigger bodies, and **defaults to preflight without any mutation**. The only optional write mode requires \`--apply\`, \`FORGE_R18_APPLY_AUTHORIZATION=INSTALL_EXISTING_FORGE_D1_ONCE\`, a distinct scoped \`CLOUDFLARE_D1_WRITE_TOKEN\` in the process environment and a PRIVATE path for the recovery bookmark (created with exclusive O_EXCL before DDL). One D1 REST batch submits only the pre-reviewed additive SQL; post-install checks exact 3-table+8-trigger namespace and unchanged unrelated schema. On ambiguous responses the installer stops; it NEVER automatically attempts a destructive restore, deploys a Worker, updates a token, or launches science.

This is an **operator script**, not a GitHub workflow action. Routine and PR CI execute mocks/local negative tests only. The preflight uses the already configured \`CLOUDFLARE_API_TOKEN\` read token. The write token must be provisioned separately only into a legitimate authorized operator session; NEVER put D1 Write in public PR CI secrets. A recovery bookmark is **not** a successfully tested backup restoration, and the private recovery file must stay in a protected, durable operator location within Cloudflare Time Travel retention.

Example from a checkout of a pinned exact FORGE commit (replace both values from the qualifying run):

\`\`\`powershell
$env:CLOUDFLARE_ACCOUNT_ID = "<account-id-from-existing-config>"
$env:CLOUDFLARE_API_TOKEN = "<read-token-in-operator-environment>"
python d1retention/install_remote.py --expected-head <exact-40-hex-commit> --expected-sql-sha256 <qualified-sha256>
# Production execution is a separate deliberate action with a scoped write token;
# do not run from public PR jobs or until the preflight succeeds.
\`\`\`

No live D1 installation is implied by the presence or success of this source module. After a legitimate operator invokes the installer with write authority, the independent read-only original evidence/first-use gate must be completed before any optimizer promotion.


## R18B — D1-specific, non-mutating table compatibility candidate

The prior [R18 live attempt](https://github.com/spoonman136668-ai/FORGE/actions/runs/38710749044) failed HTTP 400. Exact-bound postfailure query verified zero `forge_research_*` objects and an unchanged unrelated table schema. A subsequent real read-only probe proved that D1 accepts a two-SELECT REST `batch`, and also `EXPLAIN CREATE TABLE`, so neither the API batch envelope nor D1 Read itself caused the problem. Trigger `EXPLAIN` against nonexistent target tables is inconclusive. Cloudflare upstream documents remotely failing compound trigger migrations (workers-sdk #4998, #15314, #15690).

`schema_d1_compat.sql` is a separate **table-only** D1 candidate derived from the original three archival table definitions, preserving row constraints, foreign keys, uniqueness, and project identities. It intentionally does **not** include eight archive immutability/completeness triggers. This is an important **loss of database-enforced append-only protection**: a privileged D1 SQL writer could still UPDATE/DELETE and seal a partial archive. R18B is therefore limited to **DDL syntax and structural staging qualification**. It MUST NOT be accepted as a final archival or independent science custody solution without a separately reviewed, externally anchored once-only writer and verified restores; the stronger original `schema.sql` remains frozen.

`d1retention/d1_compat.py` enforces exact three-table source, bounded LF-only syntax, no DML/triggers, no prior reserved namespace, source+foreign schema hashes, in-memory-only simulation, and an explicit result that all scientific acceptance and DB immutability fields remain false. The PR workflow tests this profile offline, and its live Cloudflare probe uses **only EXPLAIN statements** to verify parsing of all three table definitions without installing them. It does not repeat the failed live write or enable new resources.
