# F139 V41 — inert cold source-transition v36 verifier

**Status:** engineering development only. This does not install a release, alter the existing `FORGE-F139-UnifiedController` task, issue #807 policy, original SQLite, owner lease or deployment source. Scientific first-use and Hybrid admission remain disabled.

## Original evidence and candidate boundary

The authentic original-owner diagnostic [run 43182527036](https://github.com/spoonman136668-ai/FORGE/actions/runs/43182527036) showed installed source `2c7caad5a4502d4b874a11d57207a35cf033eb08`, ledger event 1826 with SHA-256 `71fd4554315093d74f5a9968b4766191413cfd18d6b1ce81863f8451d379d769`, exactly 153 VERIFIED / 56 QUARANTINED historical tasks, two irrecoverably consumed publication negatives (events 1239 and 1462), 168 model attempts / 166 authenticated and 8 spent free-reasoner attempts. The owner was running but its latest 30/30 ticks reported `F139_NATIVE_CATALOG_TRUNCATED`. [PR #1719](https://github.com/spoonman136668-ai/FORGE/pull/1719) merged the exact-200 pagination fix at `7fb1bb9e0fe9439a6a7da8b66c6b0ef7acdc7595` and qualified the same tree on Windows and Linux.

## New inactive v36 contract

`f139/nci04_v41_source_transition.py` supplies a **pure cold event verifier** and a non-writing proof constructor. It requires the unique genuine installed V40 predecessor, original source exactly `2c7caad5...`, frozen event1826 anchor, preserved source-before-event SHA chain, source-filtered terminal task history, 153+ successful tasks, 56 quarantined negative tasks, exact frozen draft1239/event1462 non-retryable failures, at least 168/166 unique attempted/authenticated model publications and exactly those two unpaired negatives, exact post-V40 model-attempt source, and unchanged spent reasoner counters.

The source transition event is schema `forge.f139.source-transition.v36`, strictly seals every snapshot field, previous V40 event SHA, original event head, toolchain/binary and generator-mechanism hashes, source lineage/candidate repair anchor, and Wingless+Yggdrasil-only development policy. It rejects replay, nonexact fields, forged future attempts, Hybrid, automatic dispatch and scientific first-use.

`Database.verify` now recognizes v36 and verifies the full source event before accepting its head. The existing V2 signer and GenEnv typed execution guards now recognize exact v36 fields with a cold original SQLite replay, maintaining original one-owner guards. The existing native owner ledger also recognizes v36 as a historical source successor while retaining the exact G54 and event1464 quarantine identities. Native activation for the **new** source still requires its own separate original-owner `NATIVE_DEVELOPMENT_ACTIVATED` event; the v36 transition cannot implicitly reactivate or dispatch work. No live entrypoint, mutation writer, new worker, workflow, scheduler or queue was created.

## Boundaries not yet qualified

Positive full cryptographic cold replay on a **genuine post-V40 original Windows ledger**, exact copy/rollback and executable on that owner, original SID/task disabled and quiescent, HMAC credentials, fresh authenticated GitHub source/provider checks and incident-correct source policy, source-independent release-ref, owner-issued exact approval, post-install native intake, signed immutable release and guarded atomic source handoff **are not proven by this code**. The v36 unit positive is a field-grammar fixture, not live custody. Original owner remains on V40.

A future scoped owner release must supply the above with exactly one existing owner lease/task and genuine cold backups, and may then implement a separately reviewed installer. Never call or reuse the older V40 source cutover from `42c70d74...` on this owner; it has the wrong predecessor and historical counter predicates.
