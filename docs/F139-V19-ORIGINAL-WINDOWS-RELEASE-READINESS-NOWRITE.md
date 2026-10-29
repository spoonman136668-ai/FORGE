# F139 V19 — Original Windows owner release-readiness (read-only)

**Status:** Source-only candidate. Original Windows V18 remains the deployed owner. This gate is **not** a release, a deployment, an operator attestation, or proof of autonomous operation.

## The real deployment hazard

The V19 source integration in [#1052](https://github.com/spoonman136668-ai/FORGE/pull/1052) is qualified at `6710968e719e0685fe3aa40c5c6a93944c0e6417`, but the original Windows F139 owner and issue #807 source policy are still pinned to V18 `d8bccc604f8607bf10f9d8bc6aa568d1f98af559`. Merging without coordinating the original owner would move protected main away from the pinned installed source, interrupting new work.

The source currently exposes `transition-qualified-native-v18`, not a qualified V18-to-V19 transition command. A successful source CI run does **not** add that command or verify a live Windows SQLite backup.

## This gate

The new `v19_original_release_readonly_preflight` only reads under a held existing original `SingleOwner`: it cold verifies the actual SQLite SHA chain, V18 source, enabled/legacy-suspended metadata, empty READY/active work, and unique final V18 source-transition event. It then uses an authenticated **read-only** original GitHub client to check the full unchanged owner policy #807, protected V18 main, exact open review-ready PR #1052, and the three exact-head 6-of-6 Linux/Windows workflow runs. It repeats original and remote identity witnesses after the reads and fails closed if anything changed.

Even a successful response explicitly reports `runtime_cutover_authorized=false`, `source_transition_to_v19_implemented=false`, `installed_checkout_verified=false`, `scheduled_task_quiescence_verified=false`, `immutable_original_backup_verified=false`, and `rollback_rehearsal_verified=false`. It reports zero ledger, provider, GitHub, model or accepted-ref writes. There is **no** release or model-publish entrypoint.

## Requirements before deployment

A separately qualified V19 original-owner transition implementation must prove it preserves V18 transition ancestry and historical negative/science custody. The existing original Windows owner must independently verify scheduled task/principal/process identity, an exclusive owner lock, a cold SQLite head and no in-flight work, protected immutable release-source provenance, a cold-restorable and independently checked backup, original-user GitHub identity, and the appropriate release-policy change under an actual controlled interruption. A partial failure must hold the existing task disabled, with no second owner, no replay or write to accepted model refs.

This source-only gate uses disposable SQLite and injected Git GET fixtures. Passing hosted CI does **not** establish any of these unobserved live workstation properties, nor authorize a real provider POST, V19 draft publication or scientific first-use. Keep #1052 in RELEASE HOLD until these distinct requirements are met.
