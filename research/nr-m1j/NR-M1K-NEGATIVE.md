# NR-M1K — two-slot decision-readout falsification (post-implementation)

**Classification: SCIENTIFIC NO-GO for NR-M1J as a context-conditioned action improvement screen.** Keep this source-free negative and the original NR-M1J implementation unchanged. This audit was added **after** the NR-M1J readout/protocol code and its Linux/Windows engineering PASS, so it is retrospective diagnostic evidence, not a prospectively registered unfamiliar-world result.

## Mechanical result

`research/nr-m1j/screen.go` implements the *same* action readout for retained NR-M1E, FIFO, and reservoir memory. For each observed legal action `a`, it computes

`score[a] = sum(reward_i * exp(-distance(state_i, query)/6)) / sum(exp(-distance(state_i, query)/6))`.

Each arm retains **at most two events**. There are only two exhaustive possibilities:

1. Two events have **different actions**. Each action has exactly one contributing nonzero reward; its numerator and denominator both contain the identical context-similarity factor, so the score is simply that observed reward. The query cannot change the winning action.
2. Both events have **the same action**. No other observed action is eligible, so the chosen action is independent of query even if its numerical score varies.

If neither event has a nonzero reward, the readout abstains, also independent of query. This is not an incidental seed/fitting failure; it follows from the mathematical form and two-slot bound. The frozen implementation can still report **candidate-vs-FIFO disagreement** when their retained rewards differ, but not **context-dependent action-choice improvement**. Do not confuse such disagreement with model superiority.

## Reproducible regression

`readout_falsification_test.go` is a post-implementation source-only audit. It enumerates all 81 ordered combinations of 3x3 action IDs and 3x3 signed reward values, with two distinct predecessor public states and four sharply separated valid public queries. It checks that each combination's recommendation and abstention flag are unchanged across all query contexts. A second check applies the actual `Screen` API to candidate, FIFO, and reservoir using the existing engineering-only fixture with two different next public queries. If any action changes, the formal universal conclusion needs revision and the gate must fail closed.

No original world was reset/stepped; no original MiniGrid FIT/DEV/CHECK/HELD source was used; no native selected-action policy was run; the logged fixture's manipulated weights must **not** be reported as a learned win.

## Readiness decision

- **NR-M1J engineering code:** Existing exact-head CI for `4c5ee705f0afa94f7ebb5ac509f56539569d8e0f` passed Linux/Windows, run `41019401925`; new audit commit requires fresh exact-head CI before engineering verification.
- **NR-M1J as an NR-M1E causal action/value advantage screen:** **NO-GO** because its readout cannot depend on query context. No original source first-use or native integration justified.
- **Remaining candidate value:** NR-M1E's event-selection mechanism could later be tested with a *different prospectively frozen* downstream reader with multiple observations per legal action, real native selected decisions, truly equal trained baselines, and original-source authority. This audit does not prove NR-M1E itself always fails; it falsifies the present **two-slot normalized action readout** as a context-sensitive decision test.
- **Information mismatch:** The source-pinned older Wingless R1 public wire contains position, goal, orientation and front blockage; newer original-public MiniGrid research preserves image, heading and literal mission with seven source actions. Neither interface should be silently treated as equivalent. Inspect actual authorized native consumer and public source before any subsequent science protocol.
- **Cost and prioritization:** Do **not** patch score weights or add another hand-engineered readout to this already-seen screen and call it a new prospective experiment. Retire this particular M1J readout as a scientific candidate; use existing authentic MG35/MG36/MG37 negatives and richer native interfaces to select a genuinely decision-discriminating first-use target under separate authority. Keep FORGE autonomy untouched.

All data in this branch is advisory and does not modify protected main or accepted scientific evidence.
