# FORGE R18C — Protected Cloudflare D1 Schema Installation (2026-10-15)

**Gate:** R18C — restore database-level append-only protection and qualify a controlled original-schema installation. **Result: PASS for structural install and independently read-back protected DDL.** Scientific evidence custody, actual first-use signatures and original research ingestion remain unqualified.

## Provenance and runtime

- Existing Cloudflare Worker `curly-hat-6a9e`, existing production D1 binding `forge`. No new Worker, DB, controller or paid API resources.
- Original frozen `d1retention/schema.sql` **SHA256 `d5b3e4c1999afe1d5b61fe27a7be17c4ed446c4b85418c0859e4acf4482e765c`**.
- Existing unrelated D1 schema hash prior to and after installation: `b23212f1837fd9255597490098f7d7777db23006a89f3facc0f5d0ae3f01fac2`.
- Exact one-time installation job source commit: `a425f680552cdd0843d286e843ad1680e3cdf8ae`.
- Successful original-schema installation: [GitHub Actions #38714214616](https://github.com/spoonman136668-ai/FORGE/actions/runs/38714214616).
- Independently qualified Linux live source-to-D1 DDL comparison and Windows local-negative regression: [GitHub Actions #38714557489](https://github.com/spoonman136668-ai/FORGE/actions/runs/38714557489) — both PASS, exact source `dc6554a74448c8a0dbea82e5ef5ca2ef1390a837`.

## Engineering evidence

1. The previous REST `/query` `batch` was rejected with HTTP 400 and no persistent archive objects ([#38710749044](https://github.com/spoonman136668-ai/FORGE/actions/runs/38710749044), [#38710910558](https://github.com/spoonman136668-ai/FORGE/actions/runs/38710910558)). Existing unrelated table schema was preserved.
2. Cloudflare D1 remote `/query` accepts read-only `batch` SELECTs, while `EXPLAIN CREATE TRIGGER` on nonexistent tables is inconclusive ([#38711906068](https://github.com/spoonman136668-ai/FORGE/actions/runs/38711906068)).
3. The alternative trigger-free three-table design ([#38712452075](https://github.com/spoonman136668-ai/FORGE/actions/runs/38712452075)) was **not installed** because privileged update/delete and partial seal protection would be lost.
4. Pinned Wrangler `d1 execute --file` against an isolated **local** D1 successfully applied the original three tables plus all eight triggers ([#38713617765](https://github.com/spoonman136668-ai/FORGE/actions/runs/38713617765)).
5. An initial production workflow stopped in preflight before submission due to an unrelated foreign-table `COUNT(*)` returning HTTP 400 ([#38713782840](https://github.com/spoonman136668-ai/FORGE/actions/runs/38713782840)). It made zero D1 writes. The follow-up read-only preflight [#38714074702](https://github.com/spoonman136668-ai/FORGE/actions/runs/38714074702) qualified database identity, unchanged foreign schema and existing Time Travel bookmark without attempting protected data reads.
6. **Actual protected installation** [#38714214616](https://github.com/spoonman136668-ai/FORGE/actions/runs/38714214616) submitted the exact frozen SQL using Wrangler's file-import path with preflight bookmark saved privately in the hosted runner, no public bookmark output. Postflight independently queried `sqlite_master`: `R18C_INSTALLATION=LIVE_SCHEMA_VERIFIED`, `R18C_GUARDED_OBJECTS=11`, `R18C_FOREIGN_SCHEMA=UNCHANGED`, `R18C_DISPATCH_AUTHORIZED=FALSE`.
7. Follow-up independent read-only GitHub-hosted Linux job compared the **actual deployed text of all 11 SQL definitions** to the original SQLite compilation of `schema.sql`. It verified **8 exact trigger definitions** and 3 tables, and no unexpected additions. Cross-platform Windows checkout initially transformed LF to CRLF; source SHA guard caught drift. Scoped `.gitattributes` sets `d1retention/*.sql text eol=lf`, and the rerun [#38714557489](https://github.com/spoonman136668-ai/FORGE/actions/runs/38714557489) passed BOTH native Windows offline negatives and Linux live independent readback.

## Trust and safety boundaries

- DB-level UPDATE/DELETE immutability triggers and chunk/seal completeness triggers **are installed**. This does not stop a privileged administrator with schema modification authority from dropping triggers, nor substitute for an independently controlled signed original, first-use receipt or durable offsite evidence anchor.
- No real Wingless/Yggdrasil original was imported or executed by this work. No optimizer candidate selection or first-use authority promoted.
- The unrelated existing **schema** is verified unchanged. Its **row contents were not retrieved or independently compared**, and no row-by-row continuity claim is made. The submitted file contains only CREATE TABLE and CREATE TRIGGER definitions scoped to new `forge_research_*` names.
- Native D1 Time Travel is available; a bookmark was saved transiently in the runner before installation but **not independently retained long-term**. No destructive restore was invoked or tested. Subsequent recovery must use Cloudflare's authorized operator Time Travel mechanisms within the service's retention window.
- No synthetic production fixtures were inserted; negative mutation enforcement has been qualified against the original schema **offline**, whereas production acceptance includes exact actual DDL verification rather than destructive trigger tests.
- The original shadow-optimizer PR #233 remains a draft. No FORGE controller, KTRADE, CKB-plane, Wingless or Yggdrasil execution was modified.

## Next gate

**R19 — authentic original ingestion and independently anchored first-use custody:** use real source-pinned Wingless/Yggdrasil original artifacts and independent signed source-birth/first-use records; enforce exactly-once append via operator-scoped D1 writes; reconstruct, rehash and independently witness retained original bytes. Do not replay consumed originals, promote optimizer policies, create new research authority or claim causal gain until prospective evidence qualifies.
