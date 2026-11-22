# Eureka F49 — noise-aware consecutive-evidence change-point learner (synthetic DEV)

**Prospectively frozen on 2026-11-10 before F49 code, tests, or results.** Exact main parent `e4052145d35feca0063ae6435b2636afe94662d6`, source tree `4b68a70657613df823b9c1fadeae85bd666b5f66`. F48 SCIENTIFIC `F48_DEV_NO_GO` on draft PR #1685 remains unchanged, including F48D FIT-only diagnostic of **86 false causal-regime resets over 768 stationary FIT observations (84 noise-associated)**, report SHA `e6b18966b7cdcc19bf17602d5f5e3979b7d9728c2f5755514ba433c60509aaa4`, final source `c057373a385dbe9dcbb3128357b94d04a9ab5411`. Do not reuse its consumed heldout seeds, tune F48 thresholds, merge the F48 archive, or touch other FORGE autonomy/RSI/learning workstreams.

## New falsifiable mechanism and physical causal task

F49 tests whether **requiring corroborating independent observations before a causal-regime reset** reduces false alarms without harming genuine switch adaptation. This is NOT a claim of general intelligence, native architecture training, original Gymnasium physics, scientific first use or RSI; it is a small source-owned synthetic development environment.

State and actions: public 3-bit state `s in [0..7]`, public distinct goal `g`, requested actions {0,1,2}. Six candidate causal hypotheses for queued-action XOR effects: `EFFECTS=((1,2),(1,4),(2,4),(2,1),(4,2),(4,1))`; action 2 has no state effect but emits a noisy public binary witness indicating whether current mode >=3. The current commanded action is applied **one physical step later**, so only the *prior queued* action causes current physical change; initial pending action=2. A regime switch changes private causal mode from m to (m+3)%6 during steps **5,6,7,8**, returning to m at step 9. Agent does NOT know true mode, source seed, true noise, switch timing or realized future counterfactual state. Twelve real physical actions t=0..11 are permitted, never fewer or extra; no early stop. Reward -1 each step, final step adds +10 if state=goal else -2 × Hamming distance. Public state/goal/time/pending/action/observation/witness only.

Noise: for each seed/episode/physical step a deterministic evaluator-private unsigned 32-bit LCG generates a zero XOR disturbance with marginal probability 0.8, or one-bit XOR mask 1/2/4 with marginal probabilities 0.2/3 each; sensor witness is independently inverted with probability 0.2. The exogenous stream depends only on source seed, episode, and physical time, not selected policy, maintaining paired external conditions. All controls receive the same disclosed noise model/possible causal grammar and **only actual sampled public physical consequences**. The evaluator privately scores detection outcomes; no evaluator truth enters decisions.

## Common training, prior and fully fitted controls

FIT-only seeds `(5202,5203,5204,5205,5214,5215,5216,5217)`, modes 0..3 twice each, 12 episodes/seed × 12 physically executed open-loop actions `(0,2,1,0,1,2,0,1,0,2,1,0)`: exactly **1152 FIT action-consequence transitions**, requested action coverage [480,384,288]. Source transcripts contain only `[previous_state, prior_pending, requested, next_state, public_witness, reward, terminal]`. Fit six-mode prior with one pseudo-count per mode and posterior source-world fractional attribution learned from *public* noisy observations; no true mode labels used. Fit conventional empirical per-action XOR effect from same FIT records. Preserve exact transcript/model SHA256, FIT seed custody, positive prior support for modes 4/5 and no access to heldout until protocol/test/source fixed.

Observation likelihood for each potential mode m is `L_m = (0.8 if observed XOR matches effect(m,prior_pending), 0.2/3 if residual is one of 1,2,4, else 0) * (0.8 if sensor witness matches mode>=3, else 0.2)` only when queued command 2, otherwise witness must -1. Exact normalized Bayes update; fail closed if genuine observation receives zero likelihood under all modes. All conventional hypothesis-aware arms and candidate start from **identical FIT model/prior**.

All posterior planners choose from 0/1/2 by maximizing `sum_m posterior[m] * [2*I(s XOR effect(m,pending) XOR effect(m,action) == goal) - Hamming(s XOR effect(m,pending) XOR effect(m,action), goal)]`. This two-step model score uses only a known hypothesis grammar and public state and does **not** execute physical counterfactual actions. Deterministic lower-number action wins ties. No free probe, reserved intervention, or extra environment call.

**Novel candidate: corroborated change-point (F49):** maintain `stable` and `working` six-mode posteriors and a 3-entry log-likelihood-ratio ring buffer. Before each actually received non-sensor consequence, calculate predictive likelihood `Pstable = sum_m stable[m]*L_m` and `Palt = sum_m prior[m]*L_m` (both from public observation/known FIT grammar only), `log_ratio=log(max(Palt,1e-12)) - log(max(Pstable,1e-12))`; push into last-3 buffer. Trigger working reset to `prior` only if **at least two consecutive non-sensor log-ratios >0.5 and the sum of last three > ln(8)**. Upon reset empty the log-ratio buffer. Sensor observations clear consecutive evidence but never produce an instant reset. Otherwise update working with `(0.98*working+0.02*prior)*L`; use the same update after reset. Update stable with `normalize(0.97*stable + 0.03*working)` only when the last 3 actually observed non-sensor log-ratios are all <=0.5, and never immediately on reset. Track resets and stable updates. This is a consecutive-evidence change detector, **not** modifying F48's tested 0.12 threshold.

**Nine frozen arms:**
1. `corroborated-change` candidate (above).
2. `fixed-hazard-bayes` fully fitted control: `normalize((0.92*p+0.08*prior)*L)`.
3. `switching-hmm-bayes` fully fitted control: Markov transition `p'_m=0.88*p_m+0.12*(1-p_m)/5`, Bayesian observation update.
4. `recent3-bayes` fully fitted conventional: last 3 actual public observations recomputed via FIT prior/likelihood.
5. `no-feedback` strong conventional: fixed posterior, shared planner.
6. `trained-empirical` conventional: two-step FIT majority-effect model, same actions/goal.
7. `single-surprise-reset` mechanistic negative: baseline stable/working likelihood policy with F48-style one-observation reset when `Pworking<0.12` for non-sensor, then exact Bayes; no prior tuning.
8. `candidate-no-reset` ablation: candidate learns stable/working beliefs but disables corroborated reset, same actions.
9. `candidate-wrong-credit` negative: same candidate but computes likelihood from newly requested action instead of previously queued action; physical world action unchanged; fail-closed abstain if artificially impossible, count abstentions.

All nine arms consume identical FIT data/grammar/noise assumptions, identical *per-episode* physical action budget, and no privileged state; induced observations can differ legitimately through action choices. Independent whole-process matched-compute qualification is **not** established by identical action counts. Record actual training+evaluation duration, decision ns/action, every physical step hash, source/method bytes and model hash.

## Frozen new DEV cohorts and stationary false-alarm check

TRANSFER seeds `(5404,5405,5410,5411,5416,5417,5422,5423,5428,5429,5434,5435,5440,5441,5446,5447,5452,5453,5458,5459,5464,5465,5470,5471)`: 24 previously unseen source modes 4/5, four unique public goal tasks/seed, evaluator-only mode switch steps 5..8. RETENTION seeds `(5604,5605,5606,5607,5610,5611,5612,5613,5616,5617,5618,5619)`: 12 familiar-mode worlds (mode 0..3) with new identities, no regime switching, four public tasks each. No overlap FIT, prior F40–F48 consumed cohorts, protected first-use 59/83. Eight? **Nine arms × (24+12) worlds × 4 episodes = 1,296** synthetic scored development episodes and **1,296 independently cold restored physical/action/history replays** (exact required); each has 12 actual physical steps, 15,552 physical transitions/pass.

Additionally, before touching transfer/retention, replay all 96 already-trained stationary FIT episodes **without new physical evaluation** through `corroborated-change` and `single-surprise-reset` (both replay public FIT logs, never true hidden mode passed), and record independent false positive reset counts; no re-fitting or choosing thresholds after this audit. This is a **training-only negative control** not an independent heldout result. For a positive signal require the candidate's stationary FIT false resets <=50% of single-surprise reset's FIT false resets, with that denominator >=1.

**Precommitted `F49_DEV_SIGNAL_UNVERIFIED` only if ALL:**
- Candidate transfer success exceeds **highest** conventional (arms 2–6) by >=10 percentage points, paired strict goal-success wins in >=16/24 transfer worlds (4 tasks each), and mean transfer return >= best conventional +0.75;
- Candidate transfer success >= both no-reset and wrong-credit ablations **+10 percentage points** and >= single-surprise-reset +5pp;
- Candidate retention success >= highest conventional retention -5 percentage points;
- At least 8/24 transfer worlds have >=1 actual candidate reset and >=8/24 have >=1 candidate stable update; FIT stationary false alarms <= half of single-surprise comparator;
- 1,296/1,296 exact physical action/state/noisy-witness/reward/posterior history cold/warm comparisons, all 12 real steps, no seed/true-mode access, FIT and artifact SHA;
- Candidate per-physical-action decision time <=2× strongest conventional; elapsed fit/evaluation/total execution time must be reported separately and no matched-compute science claimed.

Otherwise **`F49_DEV_NO_GO`** for authentic complete synthetic DEV; source/custody failures block any score; focused FIT-only tests must never produce an authentic scientific claim. Preserve null/negatives/outliers, no rerun or retuning on consumed F49 DEV seeds. **Neither development label is SCIENTIFIC_PASS or RSI proof.**

## Engineering boundaries and execution

New minimal draft PR sourced from exact main `e4052145d35feca0063ae6435b2636afe94662d6`, with additive protocol `docs/NATIVE-DISCOVERY-F49-NOISE-AWARE-CHANGEPOINT-DEV.md`, `research/f49_noise_aware_changepoint_dev.py`, `research/test_f49_noise_aware_changepoint_dev.py`. Only one temporary exact PR-head-branch-scoped one-shot job in existing original `.github/workflows/qualify.yml`, to run FIT-only tests and one bounded synthetic DEV evaluation, then restore existing workflow Git blob `8b6710df902710d088fe9658da718d22244e5151` byte-exact; full original Linux+Windows 8/8 required after cleanup. No new workflow, scheduler, runner, controller, first-use, paid API, other-project scope, merge, promotion or deployment. Keep all prior negative research work intact.
