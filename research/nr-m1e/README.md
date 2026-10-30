# NR-M1E — context-conditioned, reward-only retention kernel

**Status:** ISOLATED DEVELOPMENT PROTOTYPE. Source and unit tests proposed on a draft research branch. This is not a prospective original-world protocol, accepted model, benchmark result, or source-data run.

## Distinct hypothesis

NR-M1D's learned feature-ID memory failed when the useful identifiers were reassigned. NR-M1E instead learns four *public consequence relationship* coefficients: (1) change magnitude, (2) similarity to present public context, (3) action agreement, (4) reward of observed transition. It holds exactly two observed transition events, samples replacements under a seeded two-of-three softmax, and updates its retention coefficients using **terminal reward only**. It never receives a future query, target memory, protected label or correct action.

NR-M1G added an **inert, lossless six-field public-state wire adapter**: `public_grid_adapter.go` mirrors `r1.PublicGrid`'s public `x/y/goal_x/goal_y/direction/front_blocked` values and its `PublicConsequence` reward/terminal/truncated fields. Pure converters check field types/ranges and preserve all six fields without erasure. The adapter is pinned to Wingless commit `01ca1471b60616fe323dae2ecbc0f16d053b38f3`, R1 policy blob `8d1845d82dd8578a709b00e8841bdc5edc8dbc10`, and outcome session blob `c9bc49d0993c55f0c1605ac61f4813fd51a0c083`. It does not import Wingless or run the environment. Although lossless, the candidate's six-dimensional Euclidean-like/L1 similarity still lacks semantic or causal scientific qualification. The strict candidate reward range [-1,+1] is narrower than Wingless's generic reward allowance; out-of-range values fail closed instead of silently rescaling. A source-owner-approved normalization is required before real source usage.

## Authentic interfaces found, **not exercised**

- Existing original MiniGrid FIT-only identity: FORGE `65df60ce53db70c20a616b2ceb10ade8c6fe8d23`, `research/lcrm01/itd02_r8_frozen_original_minigrid_01.json`, original MiniGrid source commit `7f5853792ea7f04f75614661006d87fcf949f26d`. Original source SHA and FIT/CHECK/DEV cohorts remain scoped to **that** historical experiment.
- The existing default-branch dispatch workflow `.github/workflows/itd02-r8-fit-only-dispatch.yml` checks out exactly that frozen source commit and runs **FIT only** under explicit manual dispatch. It grants no NR-M1E source-first-use permission.
- An earlier Wingless native draft source commit `01ca1471b60616fe323dae2ecbc0f16d053b38f3` exposes `research/native/itd02/outcome/training_session.go`, with `PublicEnvironment.ResetPublic()`, `StepPublic(action)`, and observed `PublicConsequence` / reward / terminal / truncated. Draft custody is NOT native integration acceptance. The new adapter mirrors the six source-public fields but does not claim that its feature scoring, source rights, or active integration is approved.
- Related decision standards: FORGE `docs/research-steering/LEARNING-MECHANISM-DISCOVERY.md`, `docs/research-steering/CORE-NATIVE-INTELLIGENCE.md`. Existing O10 GRU and LCRM symbolic controls are not replaced by this candidate.

## Source-only engineering checks

`policy_test.go` checks bounded two-event memory, terminal-only weight changes, simple whole-vector relabeling invariance, byte-identical continuation after cold checkpoint restoration, invalid public consequence rejection, and sensitivity to public context/action. `public_grid_adapter_test.go` checks six-field public state/return-shape round-trips, 5×5×5×5×4×2 boundary-value combinations, and fail-closed invalid directions/coordinates/rewards/actions. These are **unit tests**, not trained action-choice, unfamiliar-family transfer, or real-world benefit.

All observed binary/scalar input labels are synthetically authored by the tests; no original scientific data is consumed.

## Next admissible evidence

Before NR-M1E can claim any native decision improvement:
1. Verify current native Wingless/Yggdrasil production-of-development interface at exact immutable commit and separately establish scientific eligibility. The draft Wingless R1 and outcome source shape is now pinned with a pure converter and source-free tests; current/native runtime adoption and first-use admission remain unverified.
2. Freeze an independent *new* source-cohort and environment eligibility protocol **before** any original-world interaction or comparison.
3. Train and tune the NR-M1E retention kernel using **FIT only** and held-out CHECK for calibration only if separately permitted; keep immutable sealed original/unfamiliar sources untouched until scientific first-use authorization.
4. Use equally informed, capacity- and budget-matched trained recurrent, model-based/Bayesian, count/statistical, and symbolic controls. Include change/context/action/reward ablations and a shuffled-label shortcut test.
5. Report actual chosen-action return, seed-wise uncertainty, cold restart and interference, genuinely new causal structures, complete CPU/wall/RSS/storage/update/episode costs, source-replay identities, and negative results.
6. Only on independent qualification consider Wingless/Yggdrasil opt-in integration. Preserve each native architecture and rollback. FORGE acceptance, controller, job queue, protected main and autonomy remain unchanged.

**Decision as of authoring:** CODE CANDIDATE ONLY / SCIENTIFIC RESULTS UNVERIFIED. This study is not a reason to run the R8 first-use workflow or to merge into active native learning.
