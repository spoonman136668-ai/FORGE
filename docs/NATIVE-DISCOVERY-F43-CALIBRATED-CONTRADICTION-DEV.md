# FORGE Eureka F43 — Training-calibrated contradiction, no forced probing (DEV)

**Prospective freeze on November 10, 2026, before F43 source, tests, or evaluation.** Existing draft Eureka PR #1614 parent `5c1ac1ddb4370250c74a211fb124038f4b36cfba`, tree `d203a2203c7c8eab28af6f49102697f0aab4b877`. Preserve F40 original CartPole `F40_DEV_NO_GO`, F41 original MountainCar `F41_DEV_NO_GO` and F42 original-physics external actuator reversal `F42_DEV_NO_GO`; F42 report SHA256 `3023fb1ae7367bfdb08a46f2a2246d911391b6d2ab7c9c46a49e81a1aca989cb` was consumed. No existing results, training seeds, prior benchmarks, their protocol, source, or thresholds may change.

## Testable causal hypothesis

F42's contradiction-threshold `abs(L)>=0.9` produced zero candidate hypothesis changes despite many actual observation transitions; fixed probes impaired no-fault retention. F43 asks whether a **training-only evidence scale** and event-driven, *probe-free* contradiction switches recover from new command-channel reversals better than strongest fully trained Bayes/rolling-window adaptation and fixed MPC, without erasing clean-world ability. This is **not** an unmodified Gymnasium benchmark: the harness externally remaps requested actions while the actual `MountainCar-v0` environment handles every real state transition, reward, termination and truncation. Do not claim physical general intelligence, RSI, independent scientific pass, learning from physics unknown to the simulator or matched compute.

**Physics source:** original Farama Gymnasium exact commit `e6be96abfb0a9df36da5e7884522c4f1f2432e53`, tree `0a6e6b8c16c9b039fad21128336cecf3a13e0877`; check original ITD02 blobs, pristine Git checkout and import origin. No hidden `unwrapped` state/parameters, no true fault phase, effective actions, heldout labels or counterfactual simulator calls reach a learner. Evaluator maps `actual=2-requested` within the external fault intervals and `actual=requested` outside, preserving 1 as neutral. Only the evaluator sees the true effective action for provenance, never feeds it into policy. Freeze 200 physical steps/episode (no reset after termination), public 2D observation and actions 0/1/2.

## Frozen common training; no replay of F42 development

Common FIT transcript: F41 **training-only** seeds (811,821,827,829), 24 episodes per seed, 96 total; 18,138 physical observed transitions, action counts [7107,3011,8020]; canonical transcript SHA256 `174dee337d801c1046bd0d26b0ff0c50f89adf36cce4489c43100b4ea0dd1f34`. Reject count or digest drift. Training has no faulted action channel and all policies receive the exact same observed data. Fit the same common F41 global ridge dynamics (6×2, λ=.001), no new physics feature, no F42 heldout or new F43 evaluation used for model/calibration. Freeze source-trained model JSON bytes/hash and cold restore independently for every evaluation arm and seed.

For each non-neutral 0/2 transition in the common FIT transcript, compute the existing F42 action-contrast log-likelihood `L=((vnext - pred_normal_v)^2-(vnext-pred_reverse_v)^2)/(2*0.0025^2)`, clipped [-4,4], with the existing <=.00025 predicted-velocity separation classed uninformative. **Freeze candidate contradiction sensitivity** from only these training-only data as `tau=max(0.02,min(0.75,0.4*median(abs(L) of nonzero finite train L)))`. The multiplier, clamp and sign policy are fixed now, not fitted to previous F42 evaluation scores or any F43 heldout observations. Demand at least 1,000 informative training transitions and 0.02<=tau<=0.75, otherwise fail closed.

All source-fit policies use F41's same frozen global-linear MPC rollout (4 actions, 3^4 sequences, discount .92, cost -position-10*abs(velocity)). Their online reversal inference uses only the *actually requested action* and public observed next state, never the true effective action. Every arm gets an identical source model, task reward and physical step budget; differing choices yield differing legitimate online data. Decision-time, total wall-clock and probe counts are recorded, not assumed matched total compute.

## Preregistered nine arms (same source training)

- **calibrated-contradiction (candidate):** initial normal channel, no forced probes. After each real informative L observation, queue the most recent three L values, and switch assumed normal/reverse channel iff at least **two of those three** have opposing-sign evidence with magnitude >=tau. Clear evidence queue on a switch. For normal assumption, positive L supports reversing; for reverse assumption, negative L supports normal. Never update the physics/dynamics weights after source FIT.
- **rolling8-probe** and **rolling8-no-probe:** same F42 last-eight signed L vote; probe version uses original F42 deterministic action override at t%12==0 up to 16 probes, no-probe version uses only the planner's native commands.
- **bayes-probe** and **bayes-no-probe:** exact F42 hazard .03/likelihood Bayes online filter; same deterministic probe/no-probe pair.
- **fixed-mpc** and **velocity-rule:** original F42 unchanged conventional controls, without forced probing.
- **wrong-credit-no-probe:** same candidate policy, tau and no-probe planner, but signs of real observation likelihood L are inverted before causal hypothesis update; this is a negative *learning-credit* ablation only, not an actual reversal of the environment.
- **no-adapt-no-probe:** same source-learned MPC planner and tau computation but never changes the initial normal command mapping.

All nine get equal 96-episode source data and same physical action cap. Strongest conventional is the **one arm with highest mean reward across all four faulted DEV seeds** chosen from the six named controls (rolling8-probe/no-probe, bayes-probe/no-probe, fixed-mpc, velocity-rule). No per-world switching of the strongest baseline. A zero-probe ablation distinguishes calibration from extra physical intervention cost; the candidate must record **zero forced probes**. Negative ablations have equally heldout observations and source model. All F42 controls must remain byte-identical; no edits to F42 or earlier research sources.

## Entirely new frozen DEV challenge (no F42 outcome leakage)

Four faulted DEV seeds and *two unmodified fault-free retention* seeds are all new:

- 1409: reversals [38,94), [130,176)
- 1423: reversals [46,106), [134,180)
- 1439: reversals [42,102), [138,184)
- 1451: reversals [50,110), [140,186)
- no external fault: 1471, 1483

Windows half-open [start,end). No learner receives seed, window boundaries or fault labels. No F42 DEV seeds (1103,1117,1129,1151,1201,1213) or F41 DEV seeds (911,919,929,937,941,947,953,967) used for FIT or DEV. Protected first-use seeds **59,83 forbidden** even for a helper. Each arm starts cold on all six worlds, one original physical rollout per seed; replay independent warm session with identical actions/observations/rewards required, without reusing physical experiment result as training.

## Hard frozen scoring and stop conditions

For each of nine arms × six worlds store per-seed reward, terminations, steps, valid requested and actual action hashes (the latter evaluator-only), observation/reward hashes, initial observation, informative sample count, reversal-hypothesis flip count, 0..16 forced probes, first-fault and first-return progress, cold/warm exact physical trace equality, fit SHA/model SHA/calibration SHA and elapsed decision/whole-process timing. Store canonical report SHA256 independently re-checkable; preserve zero, tie and negative outcomes.

`F43_DEV_SIGNAL_UNVERIFIED` **only if** all of the following: candidate mean faulted-world return >= strongest selected conventional +15 *actual reward points*; candidate per-world return >= strongest +10 on at least 3/4 fault worlds; candidate mean faulted return >= each wrong-credit and no-adapt negative ablation +15; candidate mean no-fault retention >= highest conventional no-fault mean -5; candidate performs >=1 observed hypothesis change on at least 2/4 faulted worlds, with 0 forced probes; frozen training source/pin/tau, <=200 physical steps, <=16 probes/control and 54/54 cold-warm physical trace matches all PASS. Otherwise authentic completed original-physics-with-external-fault execution yields `F43_DEV_NO_GO`. Structural fixture never yields a genuine label (`F43_ORIGINAL_RUNTIME_UNVERIFIED`); absent/rejected original pinned source yields `F43_ORIGINAL_RUNTIME_BLOCKED`. F43 signal is a **development-only diagnostic**, NOT SCIENTIFIC_PASS, acceptance, autonomy/RSI, independent transfer, baseline compute parity or production.

## Scope/authority

Only append this preregistration ancestor, then add `research/f43_train_calibrated_contradiction_dev.py` and `research/test_f43_train_calibrated_contradiction_dev.py` to the existing research draft. Run structural/negative controls first. One **temporary, branch/PR-number limited** job may be appended to existing `.github/workflows/qualify.yml` to execute a single bounded DEV run in the already validated public runner; restore exact original workflow blob afterward, preserving original G141/guard and F4. Do not create any new controller, runner, scheduler, workflow, paid API, first-use, merge or deployment. Original final full Linux/Windows 8/8 and F4 2/2 remain separate mandatory engineering qualification, and the inherited G141 180s timeout is independently owned. Stop upon drift, missing evidence or exceeded scope; do not reinterpret failure as a win.
