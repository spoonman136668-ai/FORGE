# FORGE Eureka F40 — Original CartPole learning and cold-retained causal planning (DEV)

**Prospective freeze: November 10, 2026, before F40 implementation, tests, or scores.** Existing draft PR #1614. Parent SHA f90291a286027439ec736163a8b15a6e63ed92b8, tree 51b57989496c39c6c969cc6fec6ac92fd98a00e8. This is development-only research, not scientific first-use, independent acceptance, autonomous owner activation, merge, or deployment. Preserve F22–F39 negatives and independent G141/G145 guards.

## Hypothesis

Can a compact learned action-conditioned state transition model plan over real action consequences, retain training over cold restart, and outperform fully trained conventional controls on actual original CartPole-v1 episodes with unseen initial states? This is continuous state-space learning without tokenization, but one physical law: NOT novel-law transfer, autonomy, RSI or general intelligence.

## Source and custody

Use Farama-Foundation/Gymnasium original pinned Git SHA e6be96abfb0a9df36da5e7884522c4f1f2432e53, tree 0a6e6b8c16c9b039fad21128336cecf3a13e0877, ITD02 pinned blobs/import verification and pristine checkout. Run only original gym.make('CartPole-v1', render_mode=None), reset(seed=...), step(action) and close. Read only public 4-dimensional observations, rewards and termination; discard info. No internal state/physics, counterfactual simulator API, modified environment, hidden regime, or first-use seeds 59/83. No new workflow/runner/controller/scheduled task or paid API.

## Exact identical training interactions

Training seeds 601,607,613,617. For each: exactly 32 episodes, each capped to 200 real actions, with gym reset seed = training seed + 1000*episode. Behavior controller action = 1 when theta + 0.5*theta_dot >= 0, else 0; epsilon=.15 independent random action with random.Random(0xF400000 + training_seed*1000 + episode), drawing one Bernoulli per step and one uniform action on exploration. Stop immediately at original done. Log immutable tuples of full public (state, action, next state, reward, done), canonical JSON SHA256 and episode/step/action counts. Every candidate/baseline/ablation fits on exactly this one training transcript, no on-policy train, no replay environment, no extra samples.

## Portfolio frozen before scoring

(1) CAUSAL-LINEAR-MPC candidate: fit action-conditioned affine next state: x=[s0,s1,s2,s3,2*a-1,1], W=solve(X.T X + 0.001 I, X.T Y), target next 4D state; no clean truth beyond public next observation. At evaluation enumerate all 2^4 four-action sequences at each decision, predict next 4 states only with W, minimize sum of discount(.92)^h times cost 10*theta^2+0.5*thetadot^2+0.2*x^2+0.02*xdot^2, plus penalty 25 when abs(x)>2.4 or abs(theta)>0.20943951. Choose the first action of lowest-cost sequence, tie break lower action.
(2) BEHAVIOR-RULE strong conventional control: original rule without training-time exploration (a=1 if theta+0.5*theta_dot>=0).
(3) TRAINED-LINEAR-IMITATION: fit supervised ridge 0.001 over public 4D state + bias to logged action label, choose a=1 when prediction >=.5 else a=0.
(4) TRAINED-FITTED-Q: use all logged source (s,a,r,snext,done) with quadratic state features phi=[1,s0..s3,s0^2..s3^2,s0*s2,s1*s3] (11 dims), action-specific weights. Fixed 30 Bellman passes with gamma=.99 and ridge=.01, bootstrap max over actions only when not done, solve ridge normal equations each pass. Choose argmax action with lower-index tie break.
(5) WRONG-ACTION: same causal model and planner as (1), except fit with inverted logged actions. Actual physical rewards and actions unchanged.
(6) NO-LEARNED-DYNAMICS: same planner as (1), but fixed identity next-state W (no action effect).
All three learned controls and the candidate train on identical logged transitions. Behavior-rule is a deliberately strong handcrafted control not fully learned. Candidate also uses handcrafted stability objective, disclosed as a prior rather than learned intrinsic reward. No heldout feedback updates any policy.

## Exact DEV holdout and stop criteria

New heldout DEV original CartPole-v1 seeds 701,709,719,727,733,739,743,751, exactly one independent episode/seed/arm, original 500-step cap. All arms cold restore independent canonical fitted JSON; same reset seed and public action/observation interface, but realize different trajectories because of different actual actions. Record all eight actual returns, mean return, action/observation/reward hashes, done flags, model checkpoint hash, training action/episode coverage, param counts, per-decision latency, total fit cost and deterministic independent cold-vs-warm trace equality. Score against strongest of the THREE conventional arms by **mean return** across eight seeds, selected once after all scores. No per-seed cherry-picking for mean.

F40_DEV_SIGNAL_UNVERIFIED iff candidate mean >= strongest-conventional mean +20 original reward/steps; candidate >= selected conventional +10 on at least six of eight individual heldout seeds; candidate mean >= each of the two ablations +20; source and common-training custody, model validation, cold/warm exact replay, no first-use, no hidden state, no evaluation learning all PASS. Otherwise F40_DEV_NO_GO **only if real original Gymnasium runtime executed completely**. If original Gymnasium unavailable, report F40_ORIGINAL_RUNTIME_BLOCKED (not NO_GO or SIGNAL). No post-result tuning of seeds, budgets, thresholds, policies or features. Not scientific PASS, compute parity, novel physical-law transfer, RSI or autonomous deployment.

## Allowed file scope / engineering gates

Add exactly this protocol, research/f40_original_cartpole_learning_dev.py and research/test_f40_original_cartpole_learning_dev.py. Commit this protocol in immutable ancestor *before* source/tests/scores. Update the existing open draft PR #1614 only with expected-head optimistic fast-forward after focused isolated tests. No edits to workflow/owner/scheduler/G141/any older science sources. Original 8/8 Linux/Windows regression and frozen F4 2/2 on final SHA remain engineering qualification requirements. A local fake Gym interface can validate mechanics but **cannot** establish original Gymnasium scientific outcome.