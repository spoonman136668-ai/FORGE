# MP-AI06 D7 — source-pinned collision retrieval differential (2026-10-27)

**Execution:** [FORGE Windows run #40572963222](https://github.com/spoonman136668-ai/FORGE/actions/runs/40572963222), SUCCESS. Workflow source commit `7625204a5141b590470bf198919d9995c4ba0897`. D7 pinned source `536d451c0e585d22e09a2aadecf2a6cefba76402` inside the original isolated Windows runner; no accepted record writes or private content export.

## Exact method

Construct normalized-term groups from source-pinned active Mind-Palace statements, IDs, **and tags**. Use each original spelling in groups containing at least two spellings as a single-word query; compare original `MemorySnapshot.recall` with D7 `normalized_recall` under the same `continuation` budget/project. Compare returned record-ID sets, validate SHA/scope/provenance, and log counts only. This is a public diagnostic protocol on a private local source; queries are automatically selected based on the corpus and therefore **not independent scientific holdouts**.

## Original runner receipts

- `COLLISION_GROUPS=58` under expanded statement+ID+tags inventory. The earlier narrower inventory counted 57; these are **different inventory definitions**, not conflicting reproductions.
- `COLLISION_PROBES=122` original spelling queries.
- `QUERY_RESULT_SET_DIFFS=84` queries returned a different set of record IDs.
- `CANDIDATE_ONLY_MATCH_IDS=104` summed additional D7 IDs across the queries (not 104 globally distinct records).
- `BASELINE_MATCH_IDS=142`, `CANDIDATE_MATCH_IDS=205` cumulative returned record matches.
- `PROVENANCE_SCOPE_ERRORS=0`.
- `PRIVATE_RECORD_CONTENT_EXPORTED=FALSE`, `SEMANTIC_FALSE_POSITIVE_RATE=UNADJUDICATED`.

Although D7 added 104 matches relative to baseline, 205 − 142 = 63 net matches: there were also baseline-only matches. Because selected context has a fixed budget/cap, a newly admitted record may displace an old one. The original earlier 12 unrelated probes found zero candidate-only new record IDs, but the 122 collision-targeted queries reveal much wider selection changes.

## Stop / next gate

This is evidence of **behavioral retrieval divergence**, not proof of 104 false positives or 104 improvements. The result strengthens the requirement for a predeclared, independently adjudicated set of meaningful contrastive examples, with source-bound relevance labels, false-positive/false-negative accounting, and exact budgets. D7 remains development-only and unpromoted. Do not silently substitute collision-targeted probes for unseen scientific tasks; do not claim live model-answer benefit or scientific transfer.
