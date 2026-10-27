# MP-AI06 D7 unrelated-query collision audit — 2026-10-27

**Actual run:** https://github.com/spoonman136668-ai/FORGE/actions/runs/40543504843 (SUCCESS)
**Workflow source:** `7b9e659560eff8e987a3d4c998a24c2dd348747f`
**D7 source pin:** `536d451c0e585d22e09a2aadecf2a6cefba76402`

The original FORGE Windows runner evaluated 12 explicitly visible, synthetic, off-topic queries against the same source-pinned private Mind-Palace snapshot and its unchanged `MemorySnapshot.recall` baseline versus D7 `normalized_recall`. The run used no external model or paid API, exported no private record bodies, and left `.ice` and running research untouched.

## Read-only receipts

- Both baseline and D7 returned no matches on 6/12 queries.
- Both returned nonempty matches on the other 6/12.
- Baseline-only nonempty: 0; D7-only nonempty: 0.
- New D7 record IDs beyond baseline on these twelve queries: 0.
- No provenance/identity/scope errors.

**Interpretation:** no additional false-positive *retrieval candidates* were observed under these twelve synthetic queries. It is not a false-positive **rate** measurement because no independent relevance adjudicator validated the six nonempty matches, and the existing baseline already responds to some unrelated strings. Thus this does not prove that D7 is safe on all unfamiliar or distribution-shifted queries.

Keep the independently useful existing results alongside this audit:
- [D7 measured exposed development comparison](https://github.com/spoonman136668-ai/FORGE/actions/runs/40538334539): 11/12 vs 9/12 target evidence hits, candidate proxy budget 4608 vs baseline 4540, zero lost baseline hits.
- [D7 36 perturbation variants](https://github.com/spoonman136668-ai/FORGE/actions/runs/40541161304): 33/36 vs 27/36, no lost baseline hits. These variants are exposed development data.
- [D7 complete native Windows regression](https://github.com/spoonman136668-ai/FORGE/actions/runs/40525742565): PASS, protected source unchanged.

**Decision:** `D7_UNRELATED_AUDIT=PASS`; `ADDED_CANDIDATE_MATCHES=0`; `NEW_FALSE_POSITIVE_RATE=NOT_MEASURED`; `REAL_MODEL_ANSWER_GAIN=NOT_TESTED`; `SCIENTIFIC_TRANSFER=NOT_TESTED`; `PRODUCTION_PROMOTION=NOT_AUTHORIZED`.

Next meaningful gate: use a genuinely independent, pre-declared query set with source-relevance adjudication, then measure matched real-agent answer correctness and resource use. Do not merge or activate D7 as a consequence of this audit alone.
