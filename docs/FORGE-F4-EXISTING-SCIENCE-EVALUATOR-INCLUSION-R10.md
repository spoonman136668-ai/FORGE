# FORGE R10 — incorporate existing frozen F4 scientific evaluators (no original execution)

**Scientific status:** SOURCE/IMPLEMENTATION QUALIFICATION ONLY. Frozen original F4 has NOT been launched, its heldout cohort MUST remain untouched, and no independent first-use or execution authority is issued by this change.

## Exact source provenance

Preserves the previously authored F4 Go science package and immutable preregistration from FORGE's own older `f5bdadceb6601dee30db5059051fab615d937593` (unmerged F4 proposal chain #48–#53). Ten original F4 Go implementation/adversarial test files and `research/pilot-f4/frozen.json` were copied without logic changes except explicitly enumerated **pre-original source repair** below. The frozen JSON retains its **original Git blob** `76b940cae65c2800100bf1c589949bfa17ad3258` and its exact source-birth evidence. The original F4 dependency `fsagithubcustody/{audit.go,audit_test.go}` was also copied byte-for-byte from that old qualified proposal branch, restoring its unconditional `DenyAuthority` hard-stop; GitHub branch protections/rulesets cannot mint first-use. No GitHub posture requests are made during source qualification. The F4 contract remains `SYNTHETIC_ONLY` with all original train/heldout seeds, cases, controls, budgets and scientific thresholds unchanged.

- Wingless F4: fixed-capacity (10 entries), two-context role-bound two-step symbolic composition, matched unkeyed and reversed-order controls, four training and four **sealed** heldout seeds, 960 preregistered cases; comparator code is source-qualified only.
- Yggdrasil F4: 12-slot fixed-capacity protected dormancy vs capacity-matched LRU baseline, five interfering bursts, eight training and eight **sealed** heldout seeds, 160 preregistered cases; comparator code is source-qualified only.
- Both: no model calls, no oracle updates, no new capacity, no candidate tuning, no F3/F1/F2 original replay, no accepted-ref mutation.

## Bounded implementation/qualification repair

1. `pilotf4/freeze_test.go` loads the **same byte-pinned freeze** directly from the checked-out source file instead of invoking `exec.Command("git",...)`. This is necessary for the preexisting FORGE public isolation gate, which explicitly forbids arbitrary process creation outside the bounded synthetic supervisors; it does **not** change freeze or science.
2. `pilotf4/classify.go` now rejects **duplicate JSON object keys at every depth**, a scientific original-custody safety issue (previously last-write-wins semantics silently overwrote original fields).
3. A pre-original classification implementation defect was identified: the previous label calculation counted `flags[3]=true` (fixed-capacity validity) as scientific efficacy, making `NEGATIVE` **unreachable** for every otherwise valid negative experiment. `NEGATIVE` now means all **three frozen scientific efficacy comparisons failed**; `SUPPORTED` requires all three comparisons plus capacity; `MIXED` is everything in between. No metric, threshold, seed, split, or capacity changed. This correction is before **any F4 original**, and must itself be source-qualified and independently recorded before any F4 science.
4. The inherited scientific-original generator `pilotf4/primary.go` and its negative-only input tests are placed behind the default-off `forge_f4_science_unreleased` Go build tag. Ordinary FORGE builds therefore cannot call or link the F4 heldout computation at all. Enabling this tag alone still does **not** grant any first-use authority, and no workflow sets the tag for original execution.
5. New tests prove all-zero efficacy rows are preserved as `NEGATIVE` in both lanes (not mislabeled `MIXED` because capacity passed), reject nested duplicate original fields and top-level ambiguity, and reject post-freeze threshold or seed changes. Tests **never call `Primary` on a valid original**, so no protected heldout F4 was consumed during source CI.

## Gates still closed

`pilotf4.Primary` is an existing bounded evaluator entry point, not a broker/scheduler or permission to issue first-use. `CheckCustody` remains **hard-denying** until independently authenticated external first-use custody exists. Do not call `Primary` in tests, GitHub-hosted speculative builds, research sidecars or any other source-only environment. F4 cannot be admitted until the independently qualified original FSA owner, sealed frozen cohort, prior F1/F2/F3 consumed receipts, original STARTED in BOTH lanes, real worker binary/lease fencing, and immutable raw/terminal archives have been verified. CKB authority and Wingless/Yggdrasil existing research workflows remain unchanged.

**Acceptance:** exact branch Linux full `go test ./...`, race, vet, build, public isolation; native Windows full `go test ./...`, vet and build; after merge check exact Git tree and rerun source regression. This qualifies pre-original evaluator implementation, not scientific discovery, first-use, live science or cutover.
