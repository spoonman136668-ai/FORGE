# Eureka F45 — action-conditioned two-hypothesis causal tournament (DEV)

**Prospective source custody freeze, November 10, 2026, before F45 implementation, tests or data:** existing FORGE DRAFT PR #1614 head `005b59de92cf4fe23ab743495fc44789e48b4166`, tree `c27af1bddd35749d34aace4235db5311290d274e`. Previous genuine original-physics DEV results **F40, F41, F42, F43, F44 remain frozen negatives**. F44 canonical report `48d051de2a6d55e0875a6d4d720257d1cf7e986f966f5db814d3856392f1ae12` was a failure (candidate −127.5 vs rolling8-no-probe −126.125; 0/8 +10 wins) and cannot be reused to tune F45 or revise any prior score.

## Mechanism and precise testable hypothesis

Switch-based detectors model a single actuator-state hypothesis, then plan as if that chosen hypothesis were certainly true. F45 **does not change thresholds or fit a new physics regressor**. It maintains two explicit competing hypotheses about the unobserved *external* requested→physical action mapping (normal or reversed) and evaluates **one shared four-command sequence** under both, selecting the next command by model-averaged expected future physical consequences, with a small explicit diagnostic-information bonus. This uses public observations/actions and outcome likelihood, never the true hidden mapping, physical action, fault phase, privileged simulator state, future observed outcome, or full knowledge of the causal schedule. This is a different planning/information mechanism than F43's binary-gated action inversion.

Source physics remains real original Farama Gymnasium `MountainCar-v0`, Git `e6be96abfb0a9df36da5e7884522c4f1f2432e53`, tree `0a6e6b8c16c9b039fad21128336cecf3a13e0877`, original checked-out source/ITD02 blob verifier/pristine status. **The external actuator-fault wrapper is synthetic**, so the entire altered task is not unmodified original Gymnasium. Physical transitions, rewards and terminations still come directly from the original source, with no fake or alternative physics. Protected first-use (59,83) forbidden.

## Frozen common source learning

Reuse **unchanged** F43 source fit `f43.source_fit` with F41 FIT-only seeds (811,821,827,829), 96 genuine episodes, **18,138 real** source observations, all-action coverage [7107,3011,8020], exact immutable transcript SHA256 `174dee337d801c1046bd0d26b0ff0c50f89adf36cce4489c43100b4ea0dd1f34`. Common trained global linear dynamics ridge λ=.001 and source-trained tau frozen; no new model fitting, training/hyperparameter selection or heldout score access after entering DEV. All competing policies receive the exact same cold-serializable common checkpoint, observation/reward interface, 200 physical step maximum and original dynamics source. No F41/F42/F43/F44 DEV seeds reused.

Frozen source file Git blobs unchanged: `research/f41_original_mountaincar_dev.py` `ffea5f9ccc6f9b9c19eb1e9127fb985327d77a2e`, F42 `d66af2c4a734b61e36b43562071c9dfdba354768`, F43 `3a79383ec142eb08f8a60ec0c591aee3ce9a2c8e`, F44 `efb5024629f15d888d30804175a564ca45f6567a`.

## Completely frozen new F45 policy arithmetic

Each new candidate/ablation maintains `p(reverse)=0.02` initially. On each **informative** physical observation, compute the frozen F42 original-model likelihood `L=((vnext-pred_normal_v)^2-(vnext-pred_reverse_v)^2)/(2*0.0025²)` clipped [-4,4] and uninformative when predicted velocities differ by <=.00025. Before informative observation update, hazard-mix prior `p_prior=0.03+0.94*p`, then posterior `p=logistic(logit(p_prior)+L)`. This is the *same* numerical belief update as the existing fully trained F42/F43 `bayes-no-probe` control. No posterior update on L=0. Record p and belief changes. Reversal truth is absent from all calls to the policy.

For every physical time step, enumerate exactly `3^4=81` four-command **requested-action sequences** from {0,1,2}. Using only shared learned F41 dynamics, simulate the **same** sequence under hypothesis normal (physical=command) and hypothesis reversed (physical=2−command). Score each sequence under each hypothesis using frozen F41 stage objective `-predicted_position -10*abs(predicted_velocity)` with discount 0.92. Choose the sequence maximizing the posterior-weighted **sum of the two complete sequence returns**, NOT two separate mode-specific optima. Ties use original deterministic enumeration; execute only its first requested command. This is explicit causal-contingency planning, with both hypotheses experiencing the identical planned requested command sequence.

Optional information bonus (candidate only): add to each sequence score, **once for its first commanded action**, `0.04 * (4*p*(1-p)) * min(1, abs(pred_normal_next_velocity-pred_reversed_next_velocity)/0.0025)^2`; computed from source-trained predictions only, no true counterfactual physical calls. Maximum bonus .04. This is an intervention value estimate for a potentially informative 0/2 command, *not* a free extra action. No forced probes. All model-averaged arms use the exact same planner computation; only posterior evidence signs/updates and fixed bonus differ.

## Frozen eleven-arm controls/ablations

1. **hypothesis-tournament** (F45 candidate) — full posterior, shared command sequence optimization under both causal hypotheses, above fixed information bonus, no forced probes
2. **tournament-no-info** — same posterior and full model-averaged planner, bonus always zero; mechanistic information-value negative
3. **tournament-static-belief** — same planner/info bonus but posterior permanently 0.02 despite real outcomes; online learning-credit negative
4. **tournament-wrong-credit** — same planner/info bonus, but invert real likelihood evidence before updating posterior; causal-credit negative
5. **bayes-no-probe** — unchanged F43/F42 strong adaptive baseline, Bayes posterior MAP switching and single-hypothesis MPC
6. **rolling8-no-probe** — unchanged F43/F42 strong adaptive baseline
7. **rolling8-probe** — unchanged F43/F42 strong adaptive baseline with existing forced-probe policy
8. **bayes-probe** — unchanged F43/F42 strong adaptive baseline with probes
9. **calibrated-contradiction** — unchanged F43 incumbent Eureka mechanism, benchmark for forward progress
10. **fixed-mpc** — unchanged F43/F42 conventional fully trained model with no adaptation
11. **velocity-rule** — unchanged behavior rule; no physics-hypothesis inference.

Strongest *conventional* is chosen globally by the highest mean faulted reward among arms (5,6,7,8,10,11), not best per individual world; to count a F45 improvement candidate must also surpass incumbent (9) and both wrong-credit/static-belief negatives. Frozen *information bonus necessity* is separately measured as candidate versus (2), but **positive F45 result also requires ≥+5 mean over no-info**, avoiding claims of active information value from belief averaging alone. All arms receive matched observations allowed by their own real executed actions; no action cap or model data advantages. Record per-action decision time and training+evaluation whole-process time, but equal steps are NOT matched compute. Positive signal requires candidate mean decision time/physical step <=3× the stronger conventional mean ns/step; otherwise NO_GO. This is a *decision cost bound*, not whole-process parity.

## Fresh DEV scenarios and metrics (not previously consumed)

Eight new original-physics fault-channel episode seeds, each 200-step max with external hidden reversal windows half-open:
- 1801: [24,70), [112,154)
- 1811: [35,82), [121,166)
- 1823: [61,120), [154,191)
- 1831: [72,126), [151,190)
- 1847: [27,148)
- 1853: [45,160)
- 1867: [22,56), [90,126), [150,186)
- 1879: [18,62), [88,118), [149,181)

Four new genuine no-fault cold retention episode seeds (1891, 1901, 1913, 1931). Do not use any prior protected/FIT/DEV seeds 59,83,811 etc, 911+, 1103+, 1409+, 1501+, or infer fault windows from seed inside a model.

Every one of 11×12 = **132** independently reset DEV physical test episodes must be reexecuted cold-versus-warm on the exact same original source, independently replaying full real action sequences; expected **132/132 exact action/observation/reward trace matches**. True effective action only in evaluator-only hash (never passed to policy). Record seed/returns/action counts/probes, hypothesis posterior state, action/observation/reward hashes, end state, model/source SHA, informative evidence count, parity, training/decision timing and wall clock.

## Preregistered stop and classification

**`F45_DEV_SIGNAL_UNVERIFIED` only if all**:
- Candidate faulted-world mean reward >= strongest conventional + **15** and >= unchanged F43 incumbent + **15**;
- Matched individual-seed improvement >= **10** versus the selected strongest conventional on at least **6/8** faulted seeds;
- Candidate faulted mean >= each wrong-credit and static-belief ablation mean + **15**, and >= no-info mean + **5**;
- Candidate mean no-fault reward >= highest conventional no-fault mean − **5**, and candidate never uses forced probes;
- Physically valid action/reward/termination/first-use/source-fit/source Git/pristine checks, and 132/132 independent cold-warm true trace matches;
- Candidate faulted-world average **decision nanoseconds per real executed step <=3×** selected conventional, nonzero on both, no skipped controls.
Otherwise, with authentic source and all arms evaluated, `F45_DEV_NO_GO`. Missing/pristine-bad original source `F45_ORIGINAL_RUNTIME_BLOCKED`. Any fake/original-interface fixture must classify `F45_ORIGINAL_RUNTIME_UNVERIFIED` irrespective of score. Development-only signals do NOT establish SCIENTIFIC_PASS, broad generalization, autonomous RSI, matched whole-process cost, promotion, first-use or deployment. Preserve all negatives and outliers, no post-score threshold/method edits or reruns on consumed DEV seeds.

## Engineering and authority scope

Add only this frozen preregistration Git ancestor **before** source/tests, then `research/f45_causal_hypothesis_tournament_dev.py` and `research/test_f45_causal_hypothesis_tournament_dev.py` in existing DRAFT PR #1614. Focused negative tests first. A PR/head/branch-restricted **temporary job** in existing `.github/workflows/qualify.yml` may run a single original-physics DEV evaluation on the same known working public Ubuntu runner, then original workflow blob `8b6710df902710d088fe9658da718d22244e5151` must be restored byte-exact and final source checked. Do not create a new workflow/controller/scheduler/runner, or touch F43 or prior sources, protected first-use/owner, private research projects or paid APIs. The inherited G141 180-second Linux full-Go race bottleneck is independent engineering; do not relax/skip/raise timeout or loop identical CI. Final-source full 8/8 Linux+Windows and frozen F4 2/2 remain mandatory engineering qualifications, not automatic scientific evidence. No merge or production.
