# E-D62 — Online-learning conventional control (2026-10-30)

**Actual local execution PASS. No positive emergent-intelligence result.**

## Protocol
12 matched new exploratory seeds 37000–37011 × 4 arms = **48 test episodes**. Original E-C2 synthetic 16×16 ecological physics, 80 time steps, local resource observation, energy-conserving accounting. Evolve fitness and random-parent comparison underwent original three-generation training; greedy original source unchanged. New **tabular Q-learning** baseline has six starting agents, five actions (harvest or move in 4 directions), coarse discretized local resource observations, 3 training episodes with online TD updates (alpha .25, gamma .92, epsilon .20), then evaluation with frozen Q values and epsilon 0. Like original arms, Q arm evaluates with 6 agents and agent births permitted. Experimental code at session-local `/mnt/data/e_research/ed62/run_ed62.py`, results JSON `/mnt/data/e_research/ed62/results.json`. Original E-C2 source SHA-256 `1b3159224711ba46c4ef847fcce7ec1eff06ac6cd76e87d912461bf3cbe78154`. No independent custody/readback of new experiment bytes; do not claim otherwise.

## Results (mean resource harvested per action)
| Arm | Mean |
| --- | ---: |
| Q-learning online | **0.0317607490** |
| Greedy original | 0.0306713074 |
| Fitness evolution | 0.0122632042 |
| Random-parent evolution | 0.0063315149 |

Paired versus fitness evolution:
- Q-learning mean delta **+0.0194975448**, **12 wins, 0 ties, 0 losses**.
- Greedy mean delta **+0.0184081032**, **12/0/0**.
- Random-parent mean delta **-0.0059316893**, **2/1/9**.

Q-learning is ~2.59× evolution mean. Local runtime ~4.37 s. Replay of two selected Q-learning seeds PASS. Max energy-ledger residual `1.610622746284207e-11`.

## Critical qualification boundary
Q-learning's superior performance alone **does not establish online learning caused the performance**, because the baseline initializes Q=0 and greedy tie-breaking favors action 0 (harvest); the frozen evaluation's preference can be useful even without training. The Q policy receives discretized local resource states and human-defined TD updates; the evolutionary arm uses its own hand-designed genetic mechanism. No learning-disabled Q ablation, no matched observation-action architecture, no sealed holdout, no independent witness, no native Wingless/Yggdrasil implementation. Thus this is an effective *conventional control*, not proof of generalizable learning or causal cognition.

**Next scientific gate E-D63:** paired Q-learning trained vs zero-update Q agent with the **identical initialization, exploration during train, and frozen evaluation**, to determine causal value of TD learning; include greedy as a benchmark. Keep training and test seeds and generated resource trajectories matched. Preserve negative outcomes. Official MiniGrid execution blocker #1245 remains distinct. Do not alter FORGE production/autonomy.
