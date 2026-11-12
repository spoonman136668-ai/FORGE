# F139 V41 — read-only original-owner recovery preflight

**Development-only source; no owner transition, approval, dispatcher, scientific first-use, ref or task mutation.**

## Authenticated historical baseline (not a new live acceptance)
- Original Windows owner: https://github.com/spoonman136668-ai/FORGE/actions/runs/43182527036 — original FORGE-CODEX-REMOTE read-only PASS at 2026-11-12 08:24 UTC.
- Installed source and policy issue #807: 2c7caad5a4502d4b874a11d57207a35cf033eb08; original SQLite sequence 1826, head SHA-256 71fd4554315093d74f5a9968b4766191413cfd18d6b1ce81863f8451d379d769.
- Original task Running; SQLite quick_check OK; 153 VERIFIED, 56 QUARANTINED, zero READY, START_RISK or WAIT_PROVIDER. All 30 last real controller status entries: F139_NATIVE_CATALOG_TRUNCATED.
- Catalog pages were 100 + 100 + 0; old pinned source incorrectly reports overflow at exactly 200.
- Catalog fix PR #1719 merged at protected main 7fb1bb9e0fe9439a6a7da8b66c6b0ef7acdc7595, tree 6ca07ea37fc7a614e7deb22f9d0b8991b0c6e88b, with exact-source 12/12 Linux/Windows qualification and postmerge public 8/8. Do not rerun previously completed qualifications without real source or contract drift.
- Existing V40 release machinery is frozen to predecessor 42c70d74dd93ef90d0f4618fefefe2206b81eafe and original head 1462. That consumed approval/installer cannot be replayed for the currently installed 2c7caad5 release.

## New source boundary
- f139/nci04_v41_recovery_preflight.py reads a genuine original Database.open_readonly, under the externally held existing Windows kernel mutex, with an authenticated GET-only GitHub reader. It does not acquire owner authority on its own.
- Requires mode=ro/query_only, complete original db.verify() chain, installed V40 source, enabled development-only activation, no pending/uncertain work, and original verified/quarantined task-count floors.
- Requires frozen event1826/hash **as a historical ancestor, not as the current latest head**. Genuine later ledger growth is supported; current head is freshly reread under the lock.
- Verifies the sole latest V40 transition schema v35 with true predecessor 42c70d74 and destination 2c7caad5. Requires original released-source/owner-policy continuity and independently authenticated protected-main ancestry from the merged fix, with exact two fixed repair Git blob identities and final moving-main veto.
- Invokes the existing spent ref-only negative original-owner GitHub readback check. Never resets/quarantines task identities or treats synthetic data as original evidence.
- f139/test_nci04_v41_recovery_preflight.py contains source-only positive/negative controls for stale anchor, source seal drift, source/main/blob substitution, absent kernel mutex, writeable DB, pending work, insufficient history, bad target and GET provider error. Fixture tests **do not** establish original native acceptance.

## Mandatory separate original-owner recovery
A further independently qualified guarded V41 release must obtain the genuine current SID/task/runner/lease, owner-approved and read-only source-bound copy rehearsal, full original archive and signed publication-negative custody, immutable create-only release ref with no-bypass rules, mandatory exact-final Linux/Windows qualification, and an explicit original owner approval contract (not legacy V40 approval). Then, in the existing original workflow and under a fresh lock and cold backup, quiesce the SAME task and atomically change only source/policy after verifying exact current ledger head. On possible post-mutation ambiguity, hold for independent recovery, never replay.

**This change does not add a workflow/scheduled task/controller/queue, install source, mutate owner SQLite or run an original experiment.** Hybrid admission and FSA scientific first-use remain separate and denied.

Disposition on initial source commit: SOURCE_ONLY_PREFLIGHT_IMPLEMENTED; ORIGINAL_HOST_V41_ACCEPTANCE_NOT_RUN; LIVE_TRANSITION_NOT_IMPLEMENTED_OR_AUTHORIZED. CI must be read before upgrading engineering qualification.
