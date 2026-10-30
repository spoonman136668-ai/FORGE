# E-D63 — Matched Q-learning update ablation (2026-10-30)

**Local execution PASS; positive effect of TD updates in exploratory synthetic E-C2 ecology. Scientific first-use NOT accepted.**

## Method
Reused E-D62 source without changing environment physics. A Python AST transformation added an `update` parameter to `q_episode` and changed only its TD update guard from `if not test` to `if not test and update`. Both Q arms use identical empty Q initialization, random seeds, 3 training episodes per seed, epsilon 0.20 during training, shared observation discretization and frozen epsilon-zero evaluation. Comparison with unmodified greedy and fitness evolution. Matched seeds 38000–38011; 12 seeds × 4 evaluation arms = **48 evaluation episodes**. Q training exposure is 3 episodes per Q arm per seed, not counted as evaluation. The no-update arm still creates Q state entries but all action values remain zero. Training with TD updates may alter visited states and subsequent random draws through policy-induced state changes; the experiment isolates the learning-update intervention, not identical environmental trajectories.

## Results
| Arm | Mean harvested resource/action |
|---|---:|
| Q-learning TD updates enabled | **0.03186499018406836** |
| Q-learning TD updates disabled | 0.006662738639236988 |
| Greedy original | 0.030730306388284126 |
| Fitness evolution | 0.012373884955466648 |

Paired Q TD minus no-update mean `+0.025202251544831376`: **12 wins / 0 ties / 0 losses** across matched seeds. Trained/disabled ratio **~4.78×**. Replay of both Q arms for first two seeds **PASS**. Maximum within-episode energy residual `1.5759837879159022e-11`. Runtime ~4.572 s.

## Custody and limitations
Original E-D62 code SHA-256 `3427467482c768442a4ab7b0472543fe5857c321f02ee25546d06d50a89c9f27`. Actual E-D63 script `/mnt/data/e_research/ed63/run_ed63.py` and raw `/mnt/data/e_research/ed63/results.json` were executed locally, but this report is only summary in FORGE; no independently witnessed source or result custody. The source uses a local absolute dependency path. The empirical TD-update effect is within a designed synthetic ecology and with a human-programmed tabular learner. No sealed holdout, matched conventional deep baseline, native Wingless/Yggdrasil intelligence, original source-pinned external benchmark, causal concept learning or unfamiliar-family transfer. Do not promote to FORGE model selection or declare emergent intelligence.

Next E-D64: distinguish exploitation of a static resource cue from retained experience by changing reward/resource dynamics under a frozen post-training policy, with matched zero-update and greedy controls; require independent evaluation before scientific first-use. DoorKey source-pinned original benchmark still separately blocked at #1245. No FORGE autonomy modifications.
