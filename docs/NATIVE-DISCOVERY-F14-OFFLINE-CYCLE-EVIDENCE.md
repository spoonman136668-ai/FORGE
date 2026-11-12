# Eureka F14 — one portable, source-bound development-cycle evidence artifact

Engineering contract recorded before F14 repository publication, November 8, 2026. Parent: existing Eureka PR #1614 exact F13 candidate `da39258c4b91d6dd073fdc4b198c64e739d2bc87`, tree `8e2613f82a9f4313fd18fabf60d77553112662ff`. Reuse existing original FORGE native mechanisms and Go qualification; no new controller, owner or scheduler.

## Missing capability and hypothesis

F8 already exports exact G1/G2 learned-state checkpoints, and F10/F13 already record strongest-control outcomes. However, those independent exports are not one bounded, portable, source-bound development-cycle artifact. F14 tests whether the existing native checkpoints and original NO_GO results can be bound, exported, cold-read back from an offline file and tamper-rejected, without modifying a running FORGE research lane or granting scientific authority.

F14 does **not** propose a new learning algorithm or an increase in benchmark accuracy. It is an engineering interoperability seam so that a future separately qualified engine can consume exactly the same source-backed negative evidence and trained state. F10's 0/6 strong-control pass and F13's 0/4 strong-control pass remain immutable; no model selection or threshold tuning is allowed.

## Implementation contract

- Add only `nativediscovery/f14_offline_evidence.go`, its native Go test and this document to the inactive Eureka research PR. Retain all F0–F13 and other FORGE contents unchanged.
- Export a single canonical UTF-8 JSON artifact containing original F8 portable bytes plus their SHA-256, exact F8 checkpoint identity, original F10 strongest-control report and original F13 delayed-drift report, with fixed `F14_DEV_NO_GO_NO_OWNER_ADMISSION` classification. Bound total artifact size to 4 MiB; never write persistent owner/research state.
- Reuse F8/F10/F13 *existing* source-bound validation. Require the F10 parent checkpoint to match the F8 checkpoint. F13 validates earlier F12/F11 and their parent negative results. External caller must supply the expected whole-artifact SHA; a new local hash alone does not establish custody.
- Reject noncanonical JSON, unknown fields, truncation, trailing bytes, corrupt checkpoints, stale/replaced parents, changed scores/classifications, forged scientific/owner flags, missing original negatives or mismatched external artifact digests. Preserve earlier negative results instead of relabeling them as progress.
- File readback in the test uses a temporary offline file only. No child process, runtime source compilation, paid API, first-use seeds, owner action, new queue, duplicate controller, scheduled task or background runner.

## Frozen gates and outcomes

ENGINEERING PASS requires the exact final candidate's original full **8/8 Linux/Windows mandatory regression**, Go race/test/vet/build, F139/GenEnv/isolation, source/tree evidence and native F14 roundtrip/forgery tests. Do not omit original tests for performance. If the Linux native 180-second deadline fails, retain the failed attempt and distinguish infrastructure/time budget from product correctness; do not raise the timeout or skip tests silently.

SCIENTIFIC remains UNVERIFIED. F14 may only report the previously proven F10/F13 development NO_GO; no independent first-use, real-world transfer, cost gain or scientific RSI is claimed. DEPLOYMENT remains INACTIVE: no merge/promotion, automatic engine execution or FORGE owner admission. A future mechanistic experiment must be separately preregistered against fully trained, strongest matched controls before any positive-science claim.

The source-bound bundle's SHA can be carried over an **existing authorized** native artifact channel later; F14 does not itself certify remote origin or grant authority to operate such a channel.
