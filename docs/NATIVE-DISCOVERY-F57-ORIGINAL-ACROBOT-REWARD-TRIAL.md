# Eureka F57 — prospective original-Acrobot episode-return trial and FSA admission contract

**PRE-REGISTERED DESIGN ONLY; NO SCIENTIFIC DISPATCH.** Frozen before F57 source/tests and before any F57 scored data. This document originates on existing draft unmerged FORGE PR #1692 from exact qualified F56 source parent `84bdd242344a00e82f89038b3cca5881cad70189`, protected main `e4052145d35feca0063ae6435b2636afe94662d6`. It is a new prospective study of **actual real episode return**, not another action-activation or one-step proxy study. F56's original-source, existing-FIT one-step result `F56_FIT_ONE_STEP_NO_GO` is unchanged and cannot be tuned after consumption. F51 `F51_DEV_NO_GO`, F52 no-trigger, frozen F53 and F54/F55 negatives/signals also remain intact.

## Non-negotiable independent execution authority

This study **MUST NOT EXECUTE** until a separately qualified FORGE-native FSA and runner deliver all the following externally authenticated evidence: exact original source/PR SHA and original upstream commit/blob, an independently authorized original experiment grant binding *this entire frozen manifest* and evaluation script blobs; verified unique first-use experiment ID, consumed/active all-lane cohort ledger and independent monotonic high-water; a durable `DISPATCH_MAY_HAVE_OCCURRED` receipt before any possible launch, independent original STARTED witness and signed terminal/cold evidence; private FORGE-only worker identity, bounded leases, isolation and explicit operator authorization for this first-use, with zero cross-project credentials/queues or owner changes. A GitHub PR, status, workflow dispatch, ordinary user text, synthetic test signature, time-based retry, or model output **cannot** satisfy these conditions. Missing/indeterminate authority => `F57_AUTHORITY_BLOCKED_NO_FIRST_USE`; **do not consume any scored seed** or self-authorize. FORGE issue #83 tracks the wider FSA blockers. No automatic retries if first-use START status is uncertain; reconcile with original FSA witness and halt. Never execute this trial in public GitHub Actions.

## Hypothesis, exact frozen existing FIT and candidate

F54/F55 demonstrated a nonzero support-gated, FIT-calibrated residual to the strong momentum heuristic on old real source states. F56 did **not** establish a robust one-step tip-height proxy advantage. The independent hypothesis is that the **frozen F54 quantile-supported action rule** improves actual Acrobot `nips` multi-step task return relative to the strongest fully specified conventional control, without degrading `book` retention, success, deterministic cold reproduction or excessive cost. The hypothesis is falsified unless **all** criteria below pass.

External original physics **only**: official Farama-Foundation/Gymnasium v1.2.3 Git commit `365080941ea3a815ac09e57a7d4ee263a142651d`, Acrobot implementation blob `28c440af281858c30e95fb6023f19923065d64fe`, pinned import provenance and authentic `gym.make('Acrobot-v1')` source, Python 3.11, NumPy 2.0.2, `OPENBLAS_NUM_THREADS=1`. Existing F51 historical `book` FIT roots `(21011,21017,21019,21023,21029,21031)`, eight episodes per root, original 8,974 real transitions, full FIT SHA-256 `63d31930006ec2f465e4becd989c1a0b922e15a0842ef991fe424074d436a31a`, F51 40-pass original regularized FQI model SHA-256 `968c8353334256634707097ff510bcbee60177253280850f7ed56f7a0c1a93a1`, support inverse/90th percentile and `np.quantile(D,0.75)` computed **from FIT only**. The prior F54 FIT-only calibrated threshold was `0.3409597822581327` Q-units. Reject any FIT/model/support/threshold drift. No retraining, calibration, hyperparameter search, online updates, or reward-based adaptation by the candidate on scored episodes.

Exactly seven policies, **same original public observation/action/reward access and per-episode maximum 500 environment transitions**, no secret world mode passed into any policy:
1. `quantile-supported` — frozen F54 action rule, theta full original FIT, 75th percentile action-gap margin, 90th percentile support filter for greedy and momentum action, momentum fallback, no online learning.
2. `momentum-rule` — strongest simple original conventional heuristic (`2 if obs[5]>=0 else 0`), no fitted weights.
3. `frozen-fqi` — original 40-pass fully trained FQI greedy, identical trained weights.
4. `always-td` — original F51 matched fully trained model with permitted bounded episode-local TD adaptation `rate=.18` and the same original action, reward and observation budget; separate fresh policy instance each episode.
5. `quantile-margin-only` — F54 ablation using identical frozen margin but no support gating.
6. `f53-fixed-margin` — original F53 fixed 4.0 Q threshold/support; unchanged negative reference mechanism.
7. `rotated-credit` — original F54 cyclically rotated action-value rows under the same support checks; fixed negative control.

The first six are candidate/conventional/ablations, seventh is the negative control; do not omit `always-td`. All controls and candidate share the *same* FIT dataset, original feature transform, and any learned-weight training budget where applicable. Record model-fit and preparation cost for every arm including zero-training momentum; report both absolute end-to-end process cost and amortized decision cost. Do not claim equal compute where it is unequal.

## Prospective cohorts — strictly reserved, NOT currently authorized or consumed

**Proposed** distinct local Acrobot `nips` TRANSFER seeds (16):
`(51011,51013,51017,51019,51021,51023,51027,51029,51031,51033,51037,51039,51041,51047,51051,51057)`.

**Proposed** distinct original `book` RETENTION seeds (8):
`(52011,52013,52017,52019,52023,52029,52031,52037)`.

These are *proposals*, not a claim of global novelty. Before any start, the independently authenticated FORGE FSA **must prove all 24 seeds absent from consumed, active, reserved, indeterminate and protected original IDs across relevant FORGE authority ledgers**, as well as disjoint from F51 FIT/transfer/retention, untouched F53 planned 410xx/420xx cohorts, protected 59/83 and all earlier protected science. Reject on collision, ambiguity or inability to prove novelty. One immutable experiment run ID allocated before dispatch. All 24 reset seeds are tested in seven policies, each in a distinct clean environment using real upstream `nips` or `book` physics; neither mode enters a policy input.

Exactly 7 x (16+8) = **168 fresh scored episodes** and **168 cold replays**, maximum 500 genuine environment steps each. Allow each episode to terminate/truncate naturally. No scored episodes may be run solely for engineering unit tests. Original unaltered rewards, physical success, termination, action trace, public observations, final policy state, steps, CPU decision nanoseconds per step, full episode wall seconds, FIT collection/fitting/calibration wall time, original source hashes and immutable first-start/terminal witnesses are mandatory. Each cold replay uses a freshly constructed policy and exact frozen model and seed; require **168/168** action, observation, original reward, terminal/truncated flag, learned state and full public trace digests match. Any uncertain start => no rerun; an indeterminate outcome is `F57_RUNTIME_OR_CUSTODY_BLOCKED`, not a scientific failure.

## Primary metric, baselines, negative control, costs, thresholds, stop

**Primary:** genuine original `nips` mean Acrobot episode return (higher is better, up to max 500 steps, original Gymnasium rewards) over the 16 frozen transfer seeds. Choose strongest fresh conventional among `momentum-rule`, `frozen-fqi`, `always-td` by highest **mean transfer original return**, ties in written order; selection from these predeclared three only. Prespecified secondary: same-seed strictly paired candidate return wins against selected strongest, real swing-up successes, `book` retention mean against best conventional `book` mean (same three), candidate-vs-rotated-credit transfer margin, number of transfer seeds with candidate deviation, exact cold replay and authentic source/compute guards. Numerical return/success claims must be sourced from actual original action-consequence steps, never pseudo-reward or F56 one-step IPS proxy.

A **development-only, scientifically unverified signal** `F57_DEV_REWARD_SIGNAL_UNVERIFIED` requires simultaneously:
- candidate mean transfer original return >= strongest conventional mean + **15.0**;
- candidate strictly beats selected strongest conventional on **at least 12/16** paired transfer seeds;
- real transfer success count no less than strongest conventional;
- candidate mean transfer return >= `rotated-credit` negative mean + **15.0**;
- candidate original-book retention mean >= best conventional original-book retention mean - **10.0**;
- candidate acts differently from momentum at least once on **4/16** transfer seeds;
- authentic source/FIT/cohort custody, equal maximum per-episode action budgets, all finite costs and complete **168/168 cold replay** PASS;
- CPU decision ns/action, training/calibration, total physics steps and *whole-process* elapsed/cost reported for all seven arms, with explicit candidate-to-strongest cost ratios; do not claim efficiency gain merely from return.

If a fully authorized, authentic, reproducible completed study misses any of these prespecified outcomes => `F57_DEV_REWARD_NO_GO`. A positive remains only **development evidence**, requiring a separate confirmatory qualified scientific trial with pre-frozen independent baseline and cohorts. No model promotion, owner acceptance, autonomy/RSI or user notification of scientific PASS from this F57 experiment.

## Bounded source-only engineering gate allowed immediately

Before FSA exists, implement **only a fail-closed standard-library manifest / admission preflight** and deterministic negative tests. It may validate frozen constants, seven arms, cohorts, source/fit/parent pins, resource budget and prospective thresholds. It **must not** implement an untrusted caller-controlled `authorized=true` bypass, access credentials, launch a worker, create a queue, consume a seed, instantiate the environment, run evaluation, or produce experimental outcomes. Preflight must return explicit `F57_AUTHORITY_BLOCKED_NO_FIRST_USE` on missing genuine FSA evidence. Public Actions may run this source-only standard-library preflight and tests, not original scored physics. Full final native Linux+Windows qualification 8/8 at final exact SHA; preserve draft PR and original workflow blob `8b6710df902710d088fe9658da718d22244e5151`. No new scheduler/owner/controller/runner, CKB-plane, paid API, credentials, merge, deployment, or disruption of Wingless/Yggdrasil/Hybrid. Store evidence in PR/Actions, not user Library.
