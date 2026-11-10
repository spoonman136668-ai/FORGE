# Eureka F34 — Delayed-event issuance-custody structural audit (DEV diagnostic)

**Frozen before F34 implementation/testing/scoring on November 9, 2026.** Parent exact F33 candidate `63cc1764fe1a11acd2d752a033f33eff0d9ebc1b`, tree `2a0be186fd28f6293b36675ea6554113aa4ecf34`, existing draft PR #1614. F33 `F33_DEV_NO_GO` 1/4 and all F22–F32 negatives remain unchanged. F34 is a **source-only root-cause diagnostic**, not a new model, no retuning, no scientific promotion, no alternative evaluator admission.

## Falsifiable question

In the real F33 environment, the simulator enqueues a causal mask at action issuance, with a due time fixed from **that action's issuing law**. In the F32/F33 learned models, `f32Due(history, now, t, template, ignorePast)` reconstructs both old and new pending actions from one **current hypothesis template**. If the physical law switches between issuance and delivery, the model can accidentally rewrite the effect and delivery time of already issued actions. Test this exact interface inconsistency using scorer-only true-law oracle templates. If even a perfect current-law template suffers, this is a structural representation defect, not an observation-noise or training issue.

## Frozen exhaustive heldover-pulse audit

Use existing F33 DEV seeds **367,373,379,383**, their exact hidden schedule and three boundaries **t=24,48,72**. For each (seed,boundary,preboundary issuance time in {boundary-2,boundary-1}, cue in 0..3), run a new F33 world with **only** that isolated action1 and all remaining actions zero. This gives 4×3×2×4=96 reproducible physical scenarios; no new seeds or first-use. At each real transition until boundary+2, record true physical register XOR change `before ^ after` and the previously issued action's due time and mask. At each time in **[boundary,boundary+2]** (3 ticks per scenario, exactly 288 tick comparisons), independently compute:
- **Issuance-custody reference**: issue `mask,lag` are fixed at issuance using the scorer-only simulator `f33Phase(seed, issue_t)` + `f32Law(old_phase,cue)`; expected effect only at `issue_t + lag - 1`. This must equal the physical observed transition for ALL 288 comparisons.
- **Current-law replay**: invoke the **actual F32 `f32Due` helper** with a trace containing only the one past action and a zero current action, using a complete template assembled from the scorer-only current `f33Phase(seed,t)` and `f32Law(current_phase,cue)`. This is a deliberately **privileged diagnostic oracle current-law template**, not a model or fair control; count incorrect masks vs true physical transition and against issuance-custody reference.

Retain per-world, per-boundary mismatch counts, a canonical JSON SHA256, all 96 issue identities, total 288 tick comparisons, number of heldover events (due after or at boundary), and a first mismatch witness with exact seed/boundary/issue/cue/t, prior/current laws, expected mask and current-replay mask. For each scenario, require that the actual world state changed exactly at the source event due transition and nowhere else.

## Frozen classification, negatives and scope

- If **any** issuance-custody reference disagrees with the simulator, classify `F34_AUDIT_INVALID` and do not claim structural diagnosis.
- Else if **at least one** of the 288 current-law replay tick predictions disagrees with the actual simulator, classify `F34_PENDING_EVENT_REINTERPRETATION_CONFIRMED`.
- Otherwise `F34_PENDING_EVENT_REINTERPRETATION_NOT_OBSERVED`; no post-result choice of cases, boundaries, threshold or witness.
This structural audit says nothing about whether a new learner improves external goal achievement, F33 accuracy or compute efficiency. No hidden law, oracle transition, or scored state is furnished to the F33/F32 model paths; the oracle lives only in the forensic test. Reject unknown/first-use seeds 59,83 and invalid t/cue, preserve F33 NO_GO untouched.

Exactly **two additive paths**: `docs/NATIVE-DISCOVERY-F34-ISSUANCE-CUSTODY-AUDIT.md`, `nativediscovery/f34_issuance_custody_audit_test.go`. Protocol-only ancestor commit before writing/running audit code or scores. No edits to F33/F32 model, experimental inputs or evaluator, no new PR, runner, schedule, queue, owner/controller, first-use, workflow, G141 timeout or research integration. Original full Linux/Windows and frozen F4 qualification on final exact SHA are engineering gates only; parallel regression owner handles G141.
