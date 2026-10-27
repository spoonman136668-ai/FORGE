# MP-AI06 D7 committed-source development measurement — 2026-10-27

## Authority and execution
- Exact pinned Mind-Palace candidate: `536d451c0e585d22e09a2aadecf2a6cefba76402` (D7 PR #115; draft, unmerged).
- Existing original isolated FORGE Windows runner: [run #40538334539](https://github.com/spoonman136668-ai/FORGE/actions/runs/40538334539), success.
- Pipeline source commit: `172a9eb014984b59fdce1acf88e222bbe1fab50e`.
- Original baseline: committed `MemorySnapshot.recall`; candidate: committed `agentic/mpai06_d7_normalized_recall.py` opt-in `normalized_recall`.
- The preexisting `_audit_one` source, scope, governance, lifecycle, provenance, budget and original record-identity checks evaluated both arms.
- Twelve already exposed D3 development cases, no novel holdout or model generation; no private record content exported, no source edits, no new credentials or paid calls.

## Original runner receipt
| Measurement | Baseline | D7 |
|---|---:|---:|
| Required evidence supplied | 9/12 | 11/12 |
| Must abstain | 3 | 1 |
| Outdated conflicting record | 1 | 0 |
| Unsubstantiated nonempty matches | 3 | 1 |
| Sum of proxy context tokens | 4540 | 4608 |

D7 gains: `dedup-before-write`, `new-vs-old-transport`. No previously passing case lost. Source-based estimated token cost +68 (+1.498%). This uses UTF-8/3 proxy, **not provider token accounting**.

## Separate engineering evidence
- [Focused source qualification #40525418151](https://github.com/spoonman136668-ai/FORGE/actions/runs/40525418151): success.
- [One full Windows regression #40525742565](https://github.com/spoonman136668-ai/FORGE/actions/runs/40525742565): success.

## Interpretation and next boundary
This is a positive **known development-case retrieval coverage** result from the actual D7 code, with slight proxy-budget regression. It is not a first-use held-out scientific result, a demonstrated model-answer gain, live ChatGPT integration, nor a production promotion. The 12 cases are already exposed to developer scrutiny. No deployment, merge, native admission, default MCP modification, original `.ice` update or controller cutover was executed.

Status: `D7_COMMITTED_SOURCE_PAIRED_DEVELOPMENT=PASS`; `SOURCE_HITS=11_OF_12_VS_9_OF_12`; `PREVIOUS_HITS_LOST=0`; `RESOURCE_PROXY_NONREGRESSION=FAIL`; `GENERATIVE_ANSWER_QUALITY=NOT_TESTED`; `SCIENTIFIC_FIRST_USE=NOT_ESTABLISHED`; `PROMOTION=FALSE`.
