# Eureka F50 — switch-capable strong controls for corroborated causal change detection (synthetic DEV)

**Prospective registration: 2026-11-10 US Eastern, BEFORE F50 source, tests or new scored data.** FORGE main parent `e4052145d35feca0063ae6435b2636afe94662d6`, tree `4b68a70657613df823b9c1fadeae85bd666b5f66`. The F49 prospective DEV in PR #1688 is **RUNTIME_BLOCKED**, not SCIENTIFIC_PASS or DEV_NO_GO, after its fixed-mode `recent3-bayes` strong control hit `F49_IMPOSSIBLE_CAUSAL_OBSERVATION`. Its attempted DEV seeds are considered consumed; final original full CI 8/8 PASS on `7b5a9fd6fad350ad1ca16c9c67e77b5702fce455`, and FIT-only failure demonstration 11/11 PASS. F48/F48D historic negatives/diagnostics stay unchanged; no use of F49 DEV outcomes to tune mechanism/thresholds. This is new *prospectively distinct* F50 with wholly new frozen cohorts.

## Scope, core falsifiable hypothesis, and limitations

Will the **pre-existing F49 corroborated multi-observation change-point mechanism (unchanged)** achieve higher real goal attainment under delayed/noisy/temporarily switching causal effects than a strong portfolio of switch-capable conventional controls? The only substantive mechanism/source difference to F49 besides fresh seeds is **repairing the previously impossible fixed-mode 3-step conventional baseline** into a source-grounded switch-capable 3-observation forward filter, *without removing, weakening, or discounting it*. Retain identical candidate posterior-update mathematics, evidence cutoffs, stable-memory update, explicit prior action credit, scoring, ablations, noise laws, rollout length and source grammar; do not retune F49 candidate to win.

This is a **synthetic source-owned 3-bit latent-causal environment**. Even a positive `F50_DEV_SIGNAL_UNVERIFIED` cannot be called independently accepted scientific improvement, general intelligence, native cognitive architecture training, RSI, new owner authorization, or real-world transfer. No prior protected first-use or independently heldout test is consumed.

## Physical environment (frozen F49 grammar/physics)

Public 3-bit state `s=0..7`, distinct public goal `g`, requested actions `0,1,2`; action 2 is an inert physical sensor. Six known causal-effect hypotheses:
`EFFECTS=((1,2),(1,4),(2,4),(2,1),(4,2),(4,1))` for queued actions 0 and 1; pending action 2 effect 0. At physical step t an evaluator-private latent causal mode m applies the **PREVIOUS** pending action via XOR, not newly requested action; then the newly requested action is queued. Initial pending=2. Transfer evaluator alone changes mode m→(m+3)%6 at physical steps **t∈{5,6,7,8}**, restores prior m at t=9. No mode/schedule/seed/physical noise exposed to any policy. **12 real action-consequence steps per episode**; final +10 if state==goal, else −2×Hamming distance, plus −1 per physical step. No early stop.

At every step source-private deterministic unsigned LCG exogenous state disturbance XOR is 0 with probability .8 or one bit {1,2,4} with .2/3 probability each; when prior pending=2, public binary witness of `m>=3` is flipped with probability .2. Noise stream depends only on source seed, task episode and physical t, so all arms face identical exogenous disturbance for matched episode/time. All agents receive only public state/goal/time/pending/observations/rewards, and possible causal templates/known stationary noise law. No calls to source's future state or true mode; counterfactuals may be computed **in model hypothesis space** only.

All hypothesis-aware arms choose new action maximizing the exact pre-existing 2-step public-goal model score `Σ_m posterior[m]*(2*I(next_hypothesis==goal)-Hamming(next_hypothesis,goal))`, with lower-number tie break. Learned empirical control uses the analogous action choice from its FIT trained majority effects. No free physical actions.

## Immutable identical FIT training information for all nine arms

Eight **entirely new** FIT seeds `(6204,6205,6206,6207,6216,6217,6218,6219)`, modes 0/1/2/3 twice each. **12 open-loop episodes per seed × 12 physical actions** `(0,2,1,0,1,2,0,1,0,2,1,0)` = **1,152 source-owned synthetic FIT transitions**, requested-action counts `[480,384,288]`. No switch in FIT, no DEV access. Reuse the F49 exact FIT-only Bayesian source-model fitting algorithm on the new public logs, one pseudocount per latent grammar mode and positive source support for unfamiliar modes 4/5; fit conventional empirical XOR majority effects from same record. Do not leak evaluator-private latent mode/noise to fitting. Canonical transcript/model SHA256 and exact Python source blob required. FIT-only tests (including actual source-owned *switching* on familiar FIT seeds) must qualify **all nine arms end-to-end through 12 actual physical steps** before any DEV seed is accessed. These switching smoke tests are FIT-only fixture/engineering qualification, not independent science.

## Strong portfolio and exact mechanism freeze

The original F49 code `research/f49_noise_aware_changepoint_dev.py` at Git blob `6ef6eac5fea652811f1dbc02f5de62c7f20e8494` is a frozen **mechanistic starting point, not a dependency added to main**. Copy its source to a self-contained `research/f50_switching_causal_changepoint_dev.py`, change F49 source/report identifiers to F50, change FIT/DEV seed lists as here, and replace only the previously impossible `recent3-bayes` arm with `recent3-switch-bayes` specified below. All candidate and other control mathematics, thresholds (.5, ln8, .12, hazards .02/.08/.12, stable .03), timing and scoring remain untouched.

1. **corroborated-change candidate** = original F49 fixed source exactly: two consecutive non-sensor log Bayes factor >0.5 AND sum of last three >ln8 resets working posterior to FIT prior; stable memory update 0.97/0.03 only on three quiet observations; exact queued-action credit.
2. **fixed-hazard-bayes** = original F49 conventional `(0.92*p +0.08*fit_prior)*L`.
3. **switching-hmm-bayes** = original F49 conventional 6-state Markov transition `0.88*p_m+0.12*(1-p_m)/5`, then public observation likelihood.
4. **recent3-switch-bayes** = **NEW fully fitted conventional fix:** maintain the last three real public `(pending,observed_effect,witness)` tuples per episode; reinitialize six-mode weights at the common FIT prior at each step, then for EACH tuple chronologically (a) advance Markov source-mode transition `pred_m=0.88*w_m+0.12*(1-w_m)/5`, (b) multiply by exact public observation likelihood for queued command `L_m`, and (c) normalize **after each observation**. No fixed-mode product across the last three; fully switch-capable, no truth/schedule/oracle, same FIT/compute and real action budgets. If a source-generated legal tuple yields zero evidence even after the Markov prior, fail-closed with error and no score. Must pass explicit cross-mode FIT-only negative control that failed F49's recent3 filter.
5. **no-feedback** conventional = original F49 fixed common FIT prior throughout.
6. **trained-empirical** conventional = original F49 fully fitted empirical majority effect model.
7. **single-surprise-reset** negative = original F49 reset when one public observation is <0.12; no matched-hazard changes.
8. **candidate-no-reset** negative = original candidate learning minus its actual reset.
9. **candidate-wrong-credit** negative = original candidate using *newly requested action* rather than prior physically executed action for likelihood; physical actuation unchanged, no invented source observation.

All nine arms must complete FIT-only training, switching-step smoke and first-use negative controls, and be preserved in finished report irrespective of gains.

## Entirely novel DEV cohorts, frozen criterion, no re-use

TRANSFER unseen base modes 4/5: **24 seeds** `(6400,6401,6406,6407,6412,6413,6418,6419,6424,6425,6430,6431,6436,6437,6442,6443,6448,6449,6454,6455,6460,6461,6466,6467)`; each undergoes hidden t=5–8 rule change. RETENTION familiar modes 0..3: **12 seeds** `(6600,6601,6602,6603,6612,6613,6614,6615,6624,6625,6626,6627)` without rule change. Four new public goals/tasks per seed, source-owned 12-step exogenous noise. None overlap past F40–F49 FIT/evaluation seeds or protected 59/83. **9 arms ×36 worlds ×4 tasks = 1,296 genuine synthetic DEV scored episodes + 1,296 independent cold-restored repeats; 15,552 actual physical transitions per pass**. Required 1,296/1,296 exact physical action/public state/noisy witness/reward/learner-memory parity.

Additional original F49 FIT-only stationary-record *off-policy* reset comparison before scoring: 96 FIT stationary episodes replayed through corroborated-change and single-surprise-reset; no new true world evaluation, no policy oracle. Candidate false reset count must be ≤half of single reset's (if latter has ≥1). Don't tune threshold, hazard or cohort after score.

Choose the strongest conventional among arms 2–6 by TRANSFER success rate (first listed wins exact ties). A genuine `F50_DEV_SIGNAL_UNVERIFIED` requires simultaneously:
- candidate transfer goal success **≥10 percentage points higher** than strongest conventional; at least **16/24** source worlds with greater paired 4-task success count; candidate transfer mean return ≥ strongest +0.75;
- candidate success ≥10 percentage points above **each** no-reset and wrong-credit negative, and ≥5 pp above single-surprise negative;
- candidate retention success ≥ best conventional retention success −5 pp; at least **8/24** transfer worlds with candidate actual resets and at least **8/24** with stable-memory updates;
- FIT stationary resets candidate ≤ half original single-reset count; **1,296/1,296** complete cold/warm replay; 12 real actions per episode; all source, FIT, cohort, action-credit, first-use, negative-control assertions pass;
- candidate per-real-action decision-time cost ≤2× strongest conventional, with FIT/training, evaluation, and whole-process wall times reported separately. This is a diagnostic, not a matched whole-process compute proof.

Otherwise `F50_DEV_NO_GO` **only after complete authentic scored synthetic DEV**. If any control/frozen source/runtime fails mid-evaluation: `F50_RUNTIME_BLOCKED`, consumed cohorts fenced, **NO retrospective code/control fixes or rerun on those DEV seeds**. Preserve all null/negative measurements.

## Authority, qualification, disposal

Isolated DRAFT F50 PR directly from exact main, just three persistent additive files: this protocol, `research/f50_switching_causal_changepoint_dev.py`, `research/test_f50_switching_causal_changepoint_dev.py`. Permitted single one-shot FIT-only preflight + one bounded synthetic DEV evaluation through **existing** GitHub Actions qualification workflow, branch/own-repo/draft gated, no new workflow/controller/scheduler/private runner. Remove temporary job and byte-exact restore original workflow blob `8b6710df902710d088fe9658da718d22244e5151` after one execution; full exact-final-SHA original Linux+Windows 8/8 CI required separately. No CKB-plane, paid API, owner activity, cross-model lanes, scientific first-use, merge, production activation or deployment.
