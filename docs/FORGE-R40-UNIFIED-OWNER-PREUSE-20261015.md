# FORGE R40 — Unified owner pre-use code (inactive)

R40 brings the unchanged implementations of R30/R32 native original-first-use CLI into the qualified R39 source so all current protections build and test together.

- R30 source `81d4976744aaee577158d921b6f89ff6b8e292a2`: originalclaim signed predecision and fsynced write-once local first use, no research permission.
- R32 source `bb68eb985f5cf57dbca9ce2ca074fa14e0cd4441`: `cmd/forge-owner-preuse` CLI canonical signature/source/pin verification, non-authorizing record output.
- R39 source `af4fc4df7276cffab8164f0f9a32fc2dbc74cfc8`: R36 signed decision-to-D1 candidate, R37 interrupted original no-retry reconciliation, R38 monotonic D1 candidate.
All four imported Go implementation/test blobs are exact, unchanged upstream blob SHA identities.

The exact-head Linux/Windows workflow checks focused native signature, originalclaim, non-replay, SQLite epoch and monotonic negatives and one full Go regression per platform, Linux race, vet, build. Binary artifacts contain their exact SOURCE_SHA and SHA256SUMS. These executables are code-only and cannot grant scientific execution.

**Remaining authentic science blocker:** no independently authenticated physical owner/witness signer, external monotonic current-epoch D1 authority, atomic execution-side permit enforced by the existing research worker, or admitted new original. The owner call site is uninstalled; Cloudflare D1 schema remains undeployed. Do not merge, deploy, start or re-run an original based on this synthetic-tested source.

Existing CKB-plane authority and running Wingless/Yggdrasil research remain unchanged. No new controller/FSA/schedule, paid API/Codex PR review, Cloudflare D1 migration, user account changes or KTRADE/broker actions.
