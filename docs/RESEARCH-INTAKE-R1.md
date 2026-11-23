# FORGE research intake R1 — bounded original-evidence verification

**Scope:** Read-only historical intake of Wingless and Yggdrasil research. This is a development-only source/evidence snapshot, not a scientific first-use clearance.

## Source routing

- Central cross-lane coordination: [CKB-plane issue #571](https://github.com/spoonman136668-ai/ckb-plane/issues/571); the latest reviewed evidence is [comment 6179719608](https://github.com/spoonman136668-ai/ckb-plane/issues/571#issuecomment-6179719608). This issue is an advisory finding index, not a scientific acceptance writer.
- Per-experiment frozen source: immutable PR head SHA in `reference/research-intake/20261014-initial-crosslane-pr-snapshot.json` (24 revisions: 12 each lane).
- Original byte evidence: GitHub Actions artifact and its full ZIP SHA256, separately from contained raw JSON SHA256. These hashes were recomputed from directly downloaded artifact ZIPs. Workflow conclusions and authored verdicts are not automatically accepted as scientific conclusions.

## Original evidence bytes independently reaggregated

| Field | Wingless W-F10 | Yggdrasil Y-F9 |
|---|---|---|
| Draft PR | [#191](https://github.com/spoonman136668-ai/Wingless/pull/191) | [#185](https://github.com/spoonman136668-ai/Yggdrasil/pull/185) |
| Exact source head | `fab5f094a29203a5ef1d63fb40225a3aa9a7e57f` | `714e10f9df0d036f66e4baea229470ed4fe86f04` |
| First-attempt original run | [38646170288](https://github.com/spoonman136668-ai/Wingless/actions/runs/38646170288) | [38646109265](https://github.com/spoonman136668-ai/Yggdrasil/actions/runs/38646109265) |
| Artifact ID | 11932322023 | 11932008018 |
| ZIP SHA256 | `cf160c2abe1dcc32425f89eb445a20de47ba01c5b158e4fb9242507554dbaadf` | `cc20faf2c31607ace820b2a9bd90d334b52902a2f776384f938a91884a99fb9e` |
| Contained JSON SHA256 | `f397e0f45b0f1664426bca7d5a196eacc5d131d417c9030cc276aa9342a15d92` | `669c3564d7715621e97aa345ee081912223a91c337a17bd3e7dc1c5e6f38f4af` |
| Independent raw-row count | 96 paired, 192 questions | 192 paired, 384 questions |
| Frozen model correct pairs | 0/96 | 0/192 |
| Appropriate coded upper control correct pairs | 96/96 | 192/192 |
| Defect isolated | Requested exact depth absent from frozen input interface | Typed relation roles absent from frozen input interface |
| Evidence qualification | Original ZIP digest + contained JSON digest + row-level arithmetic match | Original ZIP digest + contained JSON digest + row-level arithmetic match |
| Science authority | No new sealed F3 first-use, no independent source-birth witness | No new sealed F3 first-use, no independent source-birth witness |

Row reaggregation checks each per-case model prediction against its paired truth, counts both individual and jointly correct pairs, compares all reported score totals, verifies the conditional-label flip, and rejects inconsistent controls. For W-F10, the requested-depth pair keeps the same graph and endpoints. For Y-F9, the pair changes exactly one relation-role label with the untyped edges and endpoints unchanged. This checks **internal archived evidence**, not whether a third party truly originated the underlying cohort.

W-F10's earlier run `38645980211` failed before scientific execution due a compile error, according to issue #571. Do not classify that event as a scientific negative or silently discard it during historical backfill.

## Ongoing ingestion / scientific separation

1. Treat every PR head as a separate immutable metadata revision. Historical backfill should expand the current 24-source pilot, including negative, mixed and invalid results, without replaying original experiments.
2. Verify original Actions artifacts by exact repository, run attempt, source commit, artifact ID, ZIP digest and contained-result digest. Record a distinct scientific outcome only after relevant independent validation; record unresolved evidence as unresolved.
3. Keep Wingless and Yggdrasil distinct. Never share sealed cohort identities, transfer first-use permissions, alter F3 source freezes, or infer experiment authorization from these records.
4. The two F3 source-admission gates remain **BLOCKED** pending independently authenticated source birth, historical nonreuse and the current CKB-plane authority's signed admission. No parallel scheduler, queue consumer, credential, broker action, or accepted-ref mutation.

**R1 acceptance is limited to archival lookup and reproducible source/evidence observation.** Full historical coverage, continuing automatic synchronization and future science dispatch are separate gates.
