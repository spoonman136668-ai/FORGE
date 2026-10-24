# Shared research evidence preflight (BIO historical first)

**Goal:** reuse research knowledge across BIO, Optimizer, Mass Research, Research Charter, Wingless and Yggdrasil while preserving each architecture's independent training and scientific evaluation. This implements an isolated source-verified lookup, **not** live automatic ingestion into model weights or a new agent controller.

## Canonical shared source

The private Mind-Palace repository remains the shared research evidence source. Follow `docs/AGENTIC_IMPROVEMENT_NORTH_STAR.md` and `docs/AUTONOMOUS-RESEARCH-MEMORY-20261023.md`. Its catalog `docs/RESEARCH_EVIDENCE_CATALOG.json` currently indexes historical BIO-01–61 findings. Later BIO-62–67 documents exist but require individually pinned source verification until their index is updated. Other project evidence cannot be claimed available in this catalog until an authorized writer publishes its source-verified entries.

## Verified, private preflight

From a private, already-authorized and clean read-only checkout of Mind-Palace, obtain the exact 40-character HEAD SHA. In the FORGE checkout run:

```powershell
py -3 -B -m unittest discover -s research/bio_evidence -p 'test_*.py' -v
py -3 -B research/bio_evidence/shared_evidence_preflight.py --mind-palace-root 'C:\\path\\to\\private\\Mind-Palace' --commit <40-character-SHA> --query 'memory retention replay' --limit 5
```

### Direct private GitHub lookup (optional; no local checkout)

In an **authorized private FORGE research-planning environment**, supply the existing fine-grained Mind-Palace Contents:read token as `FORGE_MIND_PALACE_READ_TOKEN`, then run:

```powershell
py -3 -B research/bio_evidence/shared_evidence_preflight.py --private-github --query 'memory retention replay' --limit 5
```

The private API client resolves the Mind-Palace main commit exactly once and pins the catalog, index and all original file reads to that SHA. It uses GET-only `api.github.com` endpoints, refuses redirects and arbitrary content paths, bounds responses, and verifies each file's Git blob identity. Original report SHA-256 is checked against the historical finding index. The token must not be passed to a public workflow or added to this repository. This read has no effect on model training, scientific approvals or dispatch.

The CLI checks the Git HEAD, clean tracked worktree, advisory catalog/index contracts, and SHA-256 of each selected original report. It returns source-pinned evidence including negative findings, controls and limitations. Source paths requiring ZIP reconstruction fail closed rather than being silently admitted. The CLI does not clone repositories, fetch secrets, submit private records to public CI, execute source material or mutate scientific authority. All automated public tests use synthetic Git repositories, not private data.

## Shared read and feedback rule

Before proposing a mechanism, each research agent should consult the current authorized evidence snapshot and link exact source hashes in its proposal. After research, the original evidence, comparison to fitted controls, negative or positive disposition and costs should be submitted through **the existing authorized Mind-Palace classification/checkpoint route**, never directly copied to other model weights or silently promoted. A research agent's cached snapshot is advisory; refresh and check supersessions at the next planning boundary.

**This is development-only and available as an explicit private agent preflight, not an installed autonomous lookup at this stage.** Automatic lookup in active FORGE/other agent planning cycles, autonomous ingestion by the memory writer and cross-model consumer verification remain separate operational qualification tasks. Do not create another queue, controller, CKB-plane dependency or paid API. No new model integration, protected first-use, promotion or production action is authorized.
