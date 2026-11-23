# FORGE operational core R3 — live independent two-lane observation

**Status: scheduled GitHub-hosted read-only observation of Wingless and Yggdrasil. No scientific execution, policy optimization from results, acceptance or migration.**

FORGE previously could run only frozen synthetic two-lane integration tests. This increment reads the **actual current** workflow-run history from each original research repository, while allowing those repositories and their independent workers to continue progressing normally. It does **not** control their workflows.

## Source of truth and custody boundary

- Workflow `.github/workflows/forge-live-research-observer.yml`: hourly and explicit manual runs on a disposable GitHub-hosted Ubuntu runner, 5-minute total job timeout, repository/action **read-only** permissions and no alternate scheduler. Never writes to either research repository or KTRADE/CKB.
- Uses actual GitHub REST GET on `spoonman136668-ai/Wingless` and `spoonman136668-ai/Yggdrasil` for at most 50 latest workflow runs each.
- `researchobserver.Build` validates each repo and originating head repo, pinned lane name, expected GitHub run URL, id/attempt, exact head SHA, timestamp, status and appropriate conclusion; rejects unknown or foreign records, duplicates, mixed/replayed lanes and invalid input. It fingerprints the **raw bytes** for later comparison. A self-computed hash does **not** independently authenticate data.
- Emits a bounded canonical report preserving **both CI successes and CI failures** without silently dropping negative or indeterminate infrastructure events. **No CI status is assigned a scientific class.** Every row has `scientific_classification=UNVERIFIED_NOT_A_SCIENTIFIC_RESULT`, `scientific_accepted=false`, `original_first_use_reconciled=false`.
- Explicitly sets `historical_completeness_verified=false`, `scientific_evidence_authenticated=false`, `execution_authorized=false`, `accepted_ref_mutation=false`, `research_originals_executed=0`.
- Uploads the bounded read-only input snapshots and resulting observation for 30 days. This is a monitoring artifact, not a new accepted reference.
- Cross-platform Go tests exercise failures preserved as metadata, foreign head repos, URL/commit mismatch, malformed timestamps/status, duplicate or missing conclusions, and rejection of incomplete history.

## Integration limits

1. Fifty latest GitHub workflow runs is **not** historical completeness, nor proof of a frozen preregistration, sealed holdout separation, qualified original start, scientific terminal, or budget compliance. No result classification or next experiment is selected from this feed.
2. The current webhook and hourly observer can **watch** autonomous research happening under the existing Wingless/Yggdrasil repos, but FORGE is not the controller of those experiments.
3. Before using a record in portfolio selection, separately fetch and authenticate its original preregistration, immutable source/tree identity, worker evidence, sealed/cohort lineage and independent terminal classification; attach to the full consumed first-use ledger. Never infer science from a green GitHub Actions badge.
4. CKB historic S14 ambiguity and source-birth provenance remain unresolved; no original may be replayed or given competing execution authority.
5. No physical FSA trust-services are installed. The earlier multi-service architecture remains unactivated and is not necessary for this observer.

## Next hard acceptance

A source-pinned real *original scientific evidence* importer (not CI metadata), then a single durable FORGE controller that schedules new prospective science only after independently verified no-double-first-use admission; two parallel per-lane worker implementations with bounded crash recovery, five-minute nonexperiment orchestration and one final full regression, then a separately qualified cutover.

This R3 is expected to run independently of current science. It must have a green manual or scheduled observer run, including an uploaded real-data artifact, before the claim **live observational integration** is accepted.
