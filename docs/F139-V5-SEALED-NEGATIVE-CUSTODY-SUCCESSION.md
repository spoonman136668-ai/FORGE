# F139 v5 — Sealed negative-custody owner succession

## Failure that motivated this successor

On 2026-10-24, the original Windows owner remained at **event185** with
10 retained quarantined failures and 18 verified development tasks.
A source-only qualified continuity update PR #852 was merged. The guarded
one-owner migration correctly refused a prospective eleventh
`forge.f139.source-transition.v4` at
`F139_NEGATIVE_TRANSITION_BUDGET_EXHAUSTED` and rolled back the original
checkout without mutating the SQLite ledger. No provider experiments were
replayed and no event186 or 187 was accepted.

The v4 limit of ten was deliberate evidence governance; deleting or merely
raising the bound would weaken frozen custody semantics.

## Proposed bounded v5 original-owner transition

The new `forge.f139.source-transition.v5` can occur only after **exactly
ten** already-verified v4 source transitions and after independently
rechecking both original sealed negative custodians, every genuine provider
failure, all verified task receipts and the complete immutable event hash
chain. Each v5 event:

- Records the **exact SHA of the terminal tenth v4 event** as
  `v4_terminal_event_sha256`.
- Preserves original negative tickets, exact provider failure event hashes,
  old and new source identities, prior event head, no new dispatches,
  and `scientific_first_use=false`.
- Requires previously unused target SHA, correct ancestor source chain,
  no active or ready work, and a prior owner-native activation or the
  pre-existing bounded idle interrupted-transition allowance.
- Is capped to **four** prospective v5 transitions; the full previous
  v2/v3/v4 limits remain unchanged.
- Cannot be used to gain accepted scientific authority, create a
  second controller, enable live broker execution or call paid services.

The original v4 events and their limit are not edited, reclassified or
rehashed. A prior accepted negative remains negative.

## Advancement gates

1. Adversarial synthetic `f139/test_nci04_v5_sealed_negative_succession.py`
   plus all existing v4, F139 and cross-platform tests.
2. Linux/Windows full qualification, source isolation, and resource controls.
3. Source merge by the single FORGE integration owner only.
4. **Exact original-owner** disposable snapshot rehearsal: event185 =>
   proposed event186 and original native approval event187; verify unchanged
   previous 185 events and every original negative.
5. Original Windows task stopped and pinned. Patch owner-authored feeder
   policy #807 to new protected source **while the task is disabled**.
   Verify readback and protected source again before restarting that same
   task. On ambiguity, fail closed with no second task or replay.
6. Independent read-only verification of new SQLite head, owner process and
   source-bound feeder. Test new research-only data additions without
   another source migration.

The last two steps must not be claimed completed by source-only CI.
