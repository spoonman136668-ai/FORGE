# R29 — Connect real research observation to advisory choice evidence

## Purpose and current limit

Use the **existing hourly** `.github/workflows/forge-live-research-observer.yml` instead of adding a scheduler, controller, FSA or Cloudflare resource. The existing observer already retrieves the actual Wingless/Yggdrasil GitHub PR metadata. R29 adds an exact-source-identified **advisory choice event**, so each qualifying observer run preserves what FORGE *could see and rank* for each existing lane at the time of observation.

This is an **observable advisory decision on genuine GitHub source**, not an experiment selection made by the existing scientific authority and **not** a prospective randomized decision. The PR metadata may already include completed experiments and outcomes, so the record explicitly denies pre-outcome timing. Do not use it as Dream-RSI `RANDOMIZED_PROPENSITY_AUDITED` history, scientific improvement, independently witnessed source birth, or first-use clearance.

## Exact producer and custody

The existing `forge-live-research-observer.yml`:
1. Fetches *real* PRs from the two existing science repositories using read-only GitHub credentials and archives the original JSON snapshots.
2. Builds the same source-pinned `pr-snapshot.json` already consumed by the cross-lane research intake.
3. Calls new `scripts/r29_live_advisory_decision.py` to calculate a deterministic, explicitly **OBSERVATIONAL** choice per lane (most recently updated source PR, latest 3 candidates retained). Every PR/head identity is bound to the original full Git commit SHA and its real GitHub link; both lanes remain separate. The output includes the raw source SHA-256, observer workflow run ID and per-choice identity hash.
4. Saves `research-decision-observation.json` in the **existing** research PR observation artifact, and hashes it together with its genuine source files for integrity. This is GitHub-hosted archival custody, **not** independent external signer/high-water protection.
5. Fails closed on malformed, foreign, stale-format, duplicate or missing lane/source records. Includes native Go and Python validation on Linux and Windows.

The run has zero privileged write permissions, no action to select an original on behalf of CKB, no Cloudflare write and no paid API. The newly added one-time R29 GitHub-hosted acceptance uses the same actual public APIs and archives the result separately to prove the producer works at exact candidate source HEAD before integration. No original or training budget is consumed.

## What this DOES NOT close

A functioning metadata-based advisory producer does **not** replace owner-generated signed predecision randomized assignments. The sole current scientific authority must still produce and sign *actual* candidate selection, recorded probabilities, independently held immutable source birth, once-only first-use and STARTED/TERMINAL receipts for fresh originals. Those genuine records are the required input to qualified R27/R28P Dream-RSI prospective holdout evaluation, and no future result may leak into earlier decisions.

Existing Cloudflare D1 already contains frozen historic original artifacts under its original guarded schema, **not** a qualified protected monotonic decision ledger. R29 does not change that schema, consume its usage cap or invent custody. Persisting observations there would be a later independently qualified action, not a substitute for independent external witness and first-use authority.

## Operational use / next science

The producer now gives the existing owner a content-bound, inspectable **candidate slate and advisory choice**, generated from authentic live research inputs in the current hourly observation. The next genuine execution gate is **in the owner**: bind a new actual, approved predecision selection event to an independently protected exact source/first-use identity and a randomized comparison, then record its terminal outcome. Only after authentic owner and external witness evidence is available can `forge-prospective-shadow --single-lane` assess Dream-RSI versus four frozen baselines.

**Disposition:** R29 source-identified advisory producer qualified independently; scientific owner selection, randomization and optimizer improvement **NOT ESTABLISHED**. No merger/activation of a draft science authority, no additional controller or FSA, no KTRADE/broker contact, and no interference with active Wingless and Yggdrasil research.
