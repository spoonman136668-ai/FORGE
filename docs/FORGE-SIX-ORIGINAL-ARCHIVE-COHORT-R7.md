# FORGE R7 — six recent native original archives, no science transfer

**Status: original evidence preservation only.** The continuing Wingless and Yggdrasil research repositories retain their own working experimental workflows and accepted scientific authority. FORGE does not dispatch, modify, or classify any of these experiments.

## Source-bound cohort

The frozen manifest `reference/research-originals/20261013-six-recent-archive-cohort.json` pins the exact source repository, workflow path, original run ID/attempt, 40-hex Git SHA, GitHub artifact ID/name, and published SHA256 of the original ZIP. The six observed public original archives are:

| Lane | Experiment | Run ID | Artifact ID |
|---|---|---:|---:|
| Wingless | W-R24 | 38402305437 | 11816026990 |
| Wingless | W-R25 | 38403153761 | 11816372869 |
| Wingless | W-R26 | 38403931613 | 11815709362 |
| Yggdrasil | Y037 | 38402292358 | 11815092927 |
| Yggdrasil | Y038 | 38403159534 | 11815309149 |
| Yggdrasil | Y039 | 38403937698 | 11815774175 |

Every archive has been previously listed by GitHub Actions under its real repository and exact SHA; this manifest does **not** assert complete CKB/Wingless/Yggdrasil scientific history.

## Implementation

- The immutable six-original manifest is required to be strict/canonical JSON with sorted, unique source identities and no additional authority fields.
- `researcharchive.Verify` checks each authentic run's repository and unforked source, exact workflow path, attempt number 1, committed source SHA, artifact-to-run/source linkage, nonexpired archive, GitHub-reported ZIP digest and **actual downloaded ZIP SHA256**.
- All embedded ZIP files must be bounded, complete, regular, unique, no traversal/symlinks, and successfully decompress with verified CRC. Their names and original ZIP files are preserved; original classifications are **not altered or inferred**.
- `cmd/forge-research-archive` receives only absolute manifest and evidence directory paths. It exposes no network, broker, mutation, job dispatch, queue, or scientific acceptance API.
- A manually dispatchable/main-source-triggered GitHub-hosted job with `contents: read` and `actions: read` downloads precisely the six source-pinned GitHub original archives and their metadata, verifies all six independently, and uploads the verbatim originals and manifest/report as an acceptance artifact. Any missing, private/inaccessible, tampered or expired artifact stops; never silently substituting a rerun or new candidate.
- Each output states `scientific_classification=UNQUALIFIED_ORIGINAL_EVIDENCE_PRESERVED`, `scientific_accepted=false`, `first_use_reconciled=false`, `original_execution_authorized=false` and `complete_ckb_custody=false`.

The earlier exact-original observation of Wingless W-R39 and Yggdrasil Y056 remains preserved separately, including Y056's reported **NO_BENEFIT**. This new batch does not override or reinterpret that negative.

## Scientific and operational constraints

Archival integrity and GitHub source identities are necessary but not sufficient for scientific acceptance. We have NOT independently qualified frozen preregistration, sealed splits, source birth, scientific heldout evidence, original first-use, negative dispositions or complete CKB S09–S14 lineage. Original S14's known wake failed `S69_FROZEN_PREREG_GIT_BLOB_CHANGED` locally despite GitHub's committed file still matching its pinned Git blob; this could reflect local Windows checkout normalization or local modifications. The cause must be established from authoritative runner bytes without changing frozen hypotheses or replaying S14.

The FORGE S14 hosted observer uses its own repository-scoped GitHub token; the authenticated cross-repository CKB read is unavailable there. Do not weaken private CKB permissions, invent an original history from an empty result, or create competing owner authority. Continue original research workflows in their current repositories without interruption.

**Gate to migrate operational science:** independently authenticated *complete* first-use and terminal-result ledger with S14 reconciled; one persistent FORGE owner, action-boundary once-only fencing, two prospective frozen real scientific workers with independent certification, unattended restart and succession, then separately authorized CKB old-owner release. Keep all existing research running until that gate passes.
