# E-D65 — TD versus contextual bandit under shifted resources and cue masking (2026-10-30)

**Local engineering execution PASS. Robust transfer/retention claim FAIL.**

The existing original E-D62 tabular Q learner was compared with (i) a **trained contextual-bandit** control using identical TD updates but gamma=0; and (ii) a no-update zero-initialized Q agent. All have three training episodes on original E-C2 resource dynamics per seed, identical state representation, action space, and evaluation budget. Frozen evaluations under manually shifted clustered and sweeping resource sources, with normal observations and with the discretized state overwritten by a fixed (0,0,0) cue on the first 40 of 80 evaluation timesteps. **This is an observation corruption/intervention, not a formal memory-delay or distraction task.** 12 exploratory seeds 40000–40011, 2 resource families × 2 cue regimes × 3 arms = **144 evaluation episodes**. Original source E-D62 SHA256 `3427467482c768442a4ab7b0472543fe5857c321f02ee25546d06d50a89c9f27`.

| Regime | Trained TD | Trained contextual bandit (gamma=0) | No-update |
|---|---:|---:|---:|
| Clustered, cues intact | 0.02195409 | 0.00606932 | 0.00564117 |
| Sweeping, cues intact | 0.02584107 | 0.00884301 | 0.00726034 |
| Clustered, cues masked first 40 steps | 0.00043773 | 0.00335938 | **0.00564117** |
| Sweeping, cues masked first 40 steps | 0.00186269 | 0.00421073 | **0.00726034** |

Paired TD versus bandit, wins/ties/losses: clustered intact 10/1/1; sweeping intact 11/0/1; clustered mask 1/6/5; sweeping mask 1/6/5. Paired TD versus no-update: clustered intact 10/1/1; sweeping intact 12/0/0; clustered mask **1/0/11**; sweeping mask **1/0/11**.

Replay: all 12 first-seed combinations (three arms, two families, two cue regimes) were recomputed identically. Maximum within-episode energy conservation residual `2.1717155851419534e-11`. Elapsed wall time approximately 15.718 seconds. Raw exploratory source `/mnt/data/e_research/ed65/run_ed65.py` and result JSON `/mnt/data/e_research/ed65/results.json` remain local, NOT independently authenticated GitHub artifacts. A fully trained model-based competitor and original greedy under identical mask were **not** included. Bandit differs from TD in discount factor; zero-update arm has initial action preferences. The forced cue may be out of training distribution, so the negative result should not be interpreted as isolating cognitive memory failure.

**Conclusion:** TD policy advantage in altered resource patterns when cues intact; marked catastrophic fragility under input corruption. No robust unfamiliar-task generalization, self-developed memory, or emergent intelligence demonstrated. This is custom synthetic ecology without frozen independent holdouts or scientific first-use. The benchmark provides a negative research direction: test explicit noise/cue corruption robustness with matched controller observation interfaces and conventional model-based alternatives. FORGE owner/autonomy unchanged. DoorKey external source-pinned run remains separately blocked (issue #1245).
