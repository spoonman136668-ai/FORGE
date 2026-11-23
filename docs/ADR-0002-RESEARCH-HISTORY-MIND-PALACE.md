# ADR 0002 — FORGE research records and Mind-Palace continuity

**Status: design and offline prototype, not deployed.** Applies to the independent FORGE Scientific Authority (FSA), research controller and Wingless/Yggdrasil lanes.

## Requirement

FORGE must document **every scientific experiment**, successful or unsuccessful, independently from CKB-plane and KTRADE. It must preserve its research history continuously after approved scientific runs, not rely on chat summaries or intermittent manual notes. Two complementary layers have distinct purposes:

1. **FORGE Scientific Archive (authoritative, private).** Immutable original hypotheses and alternatives; frozen preregistration and controls; exact source/seed/split/budget identities; original one-shot start; raw stdout, stderr and exit status; terminal evidence; independent reviews; negative, mixed, invalid and indeterminate outcomes; repair provenance; accepted scientific decision *with independent authority evidence*; archival manifests and future hypotheses. Original bytes remain in FORGE-controlled private storage. Do not silently replay an experiment to fill a documentation gap.
2. **Mind-Palace (advisory, private).** Selectively retains key findings, failed approaches, architectural decisions, scientific limits, and next steps. References point back to immutable FORGE source-of-truth records. Mind-Palace is not an experiment database or the FSA and does not admit/promote/dispatch science.

A research record is necessary even if a run failed or its science could not be interpreted. Missing provenance becomes an explicit blocker, never a reason to erase the attempt.

## FORGE-owned documentation lifecycle

| Stage | Records to retain |
|---|---|
| Hypothesis | Question, mechanism, counterhypotheses, lineage, predicted outcomes |
| Preregister | Frozen metrics, thresholds, controls, cohort/seed boundaries, negative controls, budget, source pins and prereg SHA |
| Source qualification | Exact source commit/blobs, tests, regression evidence, repairs that cannot change frozen science |
| Start | FSA-owned one-shot original run/work-order identity, first STARTED receipt, consumed-cohort witness |
| Terminal | Full original raw stdout/stderr/exit, artifact identities and hashes, classifications: SUPPORTED / MIXED / NEGATIVE / INVALID / CONSUMED_INDETERMINATE |
| Review | Independent scientific audit, causal interpretation, confounds, limitations, all negatives and separately verified science acceptance |
| Archive | Immutable source/terminal/review archive manifests, linked next generation, original cohort exclusions and lessons |

The `researchlog` module is a **non-executing structural prototype**. It checks SHA-256 chain continuity, mandatory order, frozen prereg/cohort identity, one-shot primary start, evidence preservation, cross-experiment cohort collision, source repair only before primary and preservation of all classifications. It has no GitHub transport, file writer, scheduler, or scientific authority. Its hashes prove consistency, not the identity/trust of external witnesses.

**Persisting research requires a separately qualified, FORGE-private append-only store** with atomic head compare-and-swap, crash/restart recovery, signed FSA receipts, originals retained, tamper/rollback rejection and scientifically correct quarantine. This prototype does not yet implement that store.

## Mind-Palace dataflow

Retrieve Mind-Palace directly from its **private** GitHub repository using a separate read-only credential/access capability. Pin an exact Mind-Palace commit and fetch `.ice/remote-bootstrap.json`, `.ice/remote-catalog.json`, then only the relevant `__global__` and project ranges from `.ice/remote-index.ndjson`. Require matching `source.records_sha256` and retain record IDs and `source_refs`. Mind-Palace retrieval must not need CKB controller liveness, queues, mailbox, bridge, task scheduler or local-exec.

After independent review or archiving, FORGE may **propose** a bounded Mind-Palace memory candidate containing a concise finding (including negative), project, experiment ID and exact research archive evidence pointers. `researchlog.ProposeMemoryMilestone` marks these `REVIEW_REQUIRED_NOT_STAGED`; the function does not store memory or contact a service.

A future separately authorized private handoff must honor Mind-Palace's existing source-probe/dedup, deterministic `new`/`merge`/`supersede`/`archive`/`ignore`/fail-closed `review` classifier, secrets protection, accepted source-ledger identities, bounded staging and coherent validated checkpoint. It must not write curated `.ice/records.json` directly or activate unapproved automatic/background scans. Without successful classification and a verified checkpoint, do not claim a candidate was durably remembered. Only minimal metadata and links are exported: **never raw private results, sealed cohorts, tokens or private context into public FORGE/Actions**.

## Hard execution boundaries

The FORGE Controller and FSA own only FORGE research. Their queues, locks, leases, runner identities, private stores and experimental authority are distinct from both CKB-plane and KTRADE. No FORGE component receives KTRADE broker credentials, trading permission, services, production authority, accepted refs, scheduler control, or runner leases. KTRADE remains independently governed and paper-only without separate explicit authorization. Historical CKB evidence may be imported solely read-only with independent provenance and consumed-cohort protection. No CKB or KTRADE controller/runner is stopped or restarted as a result of this work.

## Acceptance prerequisites

The library needs full cross-platform/race/adversarial qualification. A separate private persistent store, direct bounded private Mind-Palace reader, and (only when authorized) Mind-Palace classifier/checkpoint handoff each require their own tests, identity pins and external authority verification. Before any live operation: qualify end-to-end crash recovery, original one-shot receipts, negatives, FSA permission boundary and simultaneous CKB/KTRADE isolation under resource limits.

**This ADR authorizes no active FORGE controller, scientific primary, secret sharing, automatic Mind-Palace writes, or resource takeover.**
