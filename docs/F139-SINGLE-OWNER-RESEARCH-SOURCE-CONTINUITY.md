# F139 — Protected research source continuity under one operational authority

## Problem demonstrated on 2026-10-24

The only original F139 Windows owner is installed at one immutable protected
commit with a source-authenticated SQLite event chain. Merging independently
qualified research-only packages #844, #845, and later RSH-03 advanced FORGE
`main` without changing the original F139 Python controller or worker code.
The whole-repository equality check correctly blocked dispatch but required
repeated owner source migrations even though the runtime was unchanged.

That protection must not be removed without replacing it with an independently
checkable restriction. It must **not** become permission to bypass testing,
change scientific authority, or accept an arbitrary protected-main advance.

## Narrow development change

`f139.nci04_source_continuity.prove_protected_research_only_advance`
accepts only read-only evidence that all of the following hold:

1. A GitHub-authenticated *protected* `main` is a strict descendant of the
   controller's deployed source pin (exact merge base; bounded committed
   forward history with no truncation).
2. The COMPLETE compare file list has at most 48 bounded text changes and
   includes **only** the explicitly isolated
   `researchfeed/*.go`, `docs/RSH-*.md`, and exact
   `fsaservice/rsh*_readonly_bridge_test.go` files.
3. There are no controller, worker, policy, secret, workflow, dependency,
   toolchain, native-source, or runtime changes, no renames/deletions,
   duplicated paths, missing diff patches, or unbounded changes.
4. Protected `main` is independently reread after compare. A moving ref
   invalidates the proof.

Only then may the existing original F139 owner recognize the pinned runtime as
still valid for **its existing** issue intake and development-only dispatch.
`f139.nci04_candidate_publisher` uses the same rule before any future owner
source-draft publication.

## Authority and safety boundaries

- One owner: existing `FORGE-F139-UnifiedController`, exact Windows SID,
  one existing SQLite mutex, one issuer, one source-pinned #807 owner policy.
- No extra scheduler, worker, GitHub queue, issue approval, paid API, model
  service, accepted-ref mutation, or scientific first-use.
- Original controller still pins its installed commit and verifies all
  historical events. A research-only change **does not append** a source
  transition and **does not grant** science authority.
- Any change to **any other path** requires existing source-migration
  qualification and explicit owner cutover. On GitHub API outage or ambiguous
  compare, fail closed rather than infer source equivalence.
- This does not authorize another chat or service to merge FORGE changes.
  FORGE operations and protected integration have one designated authority.
  Research agents deliver independent evidence and development proposals,
  not autonomous protected merges.

## Qualification and activation

Source-only until focused tests, both Linux/Windows full regression and
original-owner read-only rehearsal pass. Merge under the single designated
FORGE integration authority, then perform **one** guarded original-owner
transition from event183 while preserving ten quarantined negative attempts
and eighteen verified development outcomes. Retarget and enable owner policy
#807 only after the original Windows ledger/process proves the new source.

Subsequently, test an actual isolated research-only protected advance with
immutable GitHub compare evidence and confirm the **same** original owner
continues its existing development operations without a source migration.
Do not claim continuous candidate generation: genuine new learning
hypotheses and independently authenticated evidence remain required.
