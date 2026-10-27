# MP-AI05 consumer integration decision — 2026-10-27

## Verified receipt
[FORGE Actions 40469192624](https://github.com/spoonman136668-ai/FORGE/actions/runs/40469192624) — **PASS** for opt-in consumer on pinned Mind-Palace source `7ad7230a82e3c748aa5336b7288ad2b45d42630c`.

On 24 deterministic, source-derived queries from two recognized conversational templates: raw top-1 **10/24**, raw top-4 **13/24**; normalized top-1 **20/24**, normalized top-4 **22/24**. The disabled consumer reproduced original retrieval exactly **24/24**; unfamiliar ordinary queries reproduced unmodified retrieval **24/24**. Source identity remained pinned and protected holdout access was zero.

## Deployment and limitations
The qualified implementation is `tools/mpai05_query_normalizer.py` plus `tools/mpai05_retrieval_consumer.py` in FORGE branch `qualification/mpai05-fastpath-20261026`, not an active change to Mind-Palace's authoritative read-only API. The new consumer defaults to `enabled=False`; recognized templates are only a narrow fraction of natural requests. Existing source-derived benchmark cases cannot establish open-domain semantic retrieval gains. This is **candidate acceptance**, not science-wide promotion or autonomous live deployment.

## Decision
Keep **opt-in only**. Consumer enablement is justified for the two exact tested templates where all source identity, project scope and read-only controls remain intact. Do not claim broad retrieval improvement or model-learning gains. Preserve immediate rollback by `enabled=False`.

Next adoption boundary: identify an actual authorized FORGE Mind-Palace consumer call site, integrate behind a disabled-by-default flag, and verify equivalence for normal requests plus candidate benefit on fixed source cases. Do not change live workloads or protected holdouts for qualification.
