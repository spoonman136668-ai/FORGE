# ADR 0001 — FORGE-native scientific authority

**Status:** Approved architectural direction; design-only, **not deployed**.

## Canonical names and ownership

The independent research system is **FORGE**. Its future scientific
decision-making authority is the **FORGE Scientific Authority (FSA)**.
It is not called "CKB Scientific Authority", and CKB-plane does not own,
rename, or replace the FSA.

| Component | Owner and responsibility |
|---|---|
| FORGE Controller | FORGE-only autonomous research progression, restart/recovery, lane scheduling, budgets and independent runner allocation |
| FORGE Scientific Authority (FSA) | FORGE-only preregistration, evidence admission, novelty/causal qualification, frozen cohort and threshold governance, negative/mixed preservation, one-shot scientific-primary decisions, acceptance and promotion |
| FORGE research lanes | Isolated Wingless, Yggdrasil and independently added future programs; each has its own queue and durable state |
| FORGE execution agents | Dedicated FORGE runner pool with bounded leases, resource limits and exact immutable work orders; no existing CKB/KTRADE controller lease |
| FORGE memory adapter | Direct **read-only** Mind-Palace retrieval of the minimum relevant records with pinned source SHA and full provenance; advisory only |
| Optional legacy import adapter | Import independently authenticated historical results from CKB-plane as **unprivileged, read-only source evidence**, never as FORGE governance or execution authority |

CKB-plane's existing live controller and scientific authority retain sole
control **over their own current work and accepted records**. They are not
FSA. FORGE must not route new FORGE work through their private queues merely
because historical experiments ran there. A future transition needs a
separate, explicit, independently qualified migration contract; an upstream
source file or historical accepted result does not grant FORGE permission to
replay it.

## Required isolation

1. **Disjoint authority domains.** FSA signs and approves only
   FORGE-owned experiments. CKB-plane controls its own original experiments,
   existing accepted refs, and historical provenance. No shared writable
   science-acceptance database or promotion endpoint.
2. **Disjoint queues and locks.** FORGE controller has its own task queue,
   leases, immutable journal, watchdog and recovery logic. It does not share
   installed Windows controller PIDs, stop/restart rights, task scheduler jobs,
   runner labels or queue consumers with CKB/KTRADE.
3. **Independent compute.** Dedicated FORGE runner labels/pool or GitHub-hosted
   qualification for source tests, explicitly budgeted and noninterfering.
   Public FORGE CI must never load private research evidence or credentials.
4. **Scientific controls.** Hypotheses, metrics, test splits, thresholds,
   negative controls and budgets freeze before their evaluations. Sourced
   evidence must be independently verified; historical synthetic positives
   are not accepted as unseen external-source proof. Once-consumed cohorts
   remain consumed everywhere.
5. **One-shot execution.** Qualified FSA-issued intent, exact run identity,
   original start receipts, immutable raw output and terminal witness; any
   uncertain start blocks repeat dispatch until reconciliation.
6. **Mind-Palace does not govern science.** Its context is advisory.
   The FSA validates provenance independently; retrieved memories cannot
   alter frozen science, experiment budgets, approvals or accepted evidence.

## Mind-Palace retrieval design

Use the **private Mind-Palace repository** through an independently
authorized **read-only** integration, *outside* public CI and without
copying the private index into this public repository.

A retrieval pins one exact Mind-Palace commit, reads
`.ice/remote-bootstrap.json` and `.ice/remote-catalog.json`, checks their
`source.records_sha256` equality, then reads only bounded
`__global__` and task-relevant project line ranges from
`.ice/remote-index.ndjson`. Preserve original record IDs and
`source_refs`, enforce a context/bytes budget, and follow original source
refs for scientific claims. Never use a CKB mailbox, controller, queue,
runner, local-exec or bridge as a prerequisite for Mind-Palace reads.

Never ingest secrets, unrelated project records, raw private datasets, or
private context into public workflow logs/artifacts.

## Version migration (do not silently rewrite)

The initial source-only FORGE Go prototype was extracted from an older
shadow design. Several **historical schema strings and advisory
dispositions** still contain `ckb.research` or `CKB`. These denote
legacy compatibility, **not** the name or authority of the future FORGE
Scientific Authority. They must be replaced through separately versioned
protocol changes with explicit compatibility tests, preserving existing
historical evidence until formally reconciled. Do not rename schemas
in place or reinterpret accepted historical receipts.

The current FORGE `contracts`, `evidence`, `planner` and `quarantine`
packages provide read-only or quarantine-only primitives. They **cannot**
currently issue scientific admission, start experiments, schedule runners,
or claim FSA activation. A future FSA implementation requires its own
independent specification, qualification suite, authority database,
recovery tests and approved controlled activation.

## Acceptance gates before any live separation

- Frozen FSA identity and authority scope; no cross-system duplicate
  controller, namespace, queue or ref-writing privileges.
- Deterministic isolated scheduling, crash/restart replay, exactly-once
  intent and negative outcome preservation.
- Native Windows/Linux qualification and fault injection, including
  simultaneous CKB and FORGE shadow activity with zero interference.
- Qualified independent Mind-Palace read-only adapter with pinned exact
  source identities, bounded retrieval and malicious-input tests.
- Full end-to-end scientific trial with preregistered disjoint cohorts,
  provenance and holdouts; then unattended soak and controlled cutover.

**Present state:** Architectural decision only. No new active controller,
scientific authority, queue consumer, runner, repo sharing or migration is
established by this file.
