# E Research E-D2 — local-observation tabular learning FIT (2026-10-29)

**Engineering PASS; FIT task acquisition supported; emergent native intelligence, independent science and first-use UNVERIFIED.** Documentation-only advisory, no FORGE model, owner, controller, queue, selection, autonomy or Wingless/Yggdrasil changes.

## Executed

Python local E-D2 environment on fixed 9x9 map. Public observation shared by learner and policies: current position, relative goal vector, one construction material unit, adjacent local wall/boundary occupancy. Every policy receives the same legal-action set; move four directions, and build to remove an adjacent modifiable wall. Build spends one material and 3 energy plus one step's energy, has no reward itself; goal harvest 8. An all-height wall is at x=3,4,5 depending on environment; a separate locked x=4 world cannot be built through, is physically unreachable. BFS complete-state solver operates **evaluation-only** and is not given to the learner.

Training: tabular Q-learning with epsilon-greedy action selection and sparse positive reward on goal, six development seeds 52000–52005, 260 repeats over each of center/left/right walls = **4,680 FIT episodes**; Q state stores exactly public observations. Fixed policy, greedy-nonbuilder and random policy require no training. Evaluation: twelve new but unsealed development seeds 52020–52031 × four map modes × four controls = **192 trajectories**. Training and evaluation maps come from same map generator and family, so **no unfamiliar-family transfer evidence**.

| Policy | Center (of 12) | Left (of 12) | Right (of 12) | Locked (of 12) | Openable total |
|---|---:|---:|---:|---:|---:|
| Random | 0 | 0 | 0 | 0 | 0/36 |
| Greedy no build | 0 | 0 | 0 | 0 | 0/36 |
| Fixed programmed builder | 12 | 12 | 12 | 0 | 36/36 |
| Q learner | 7 | 5 | 7 | 0 | 19/36 |

All openable environments BFS-reachable; all locked environments BFS-unreachable. Deterministic exact replay PASS. Energy + expenditures always equals initial 110; available+placed material always equals initial 1; no negative energy. Time 1.402s and process peak RSS ~97,260 KiB in isolated container; not independently qualified compute.

**Scientific interpretation:** The Q table acquired some effective build actions without explicit heuristic instructions, but underperformed fixed constructor substantially. Greedy and random controls are weaker than a capable conventional planner. Reward's goal position is included in the observation; no information leakage from BFS to learner. The closed/locked world is a feasibility negative, not a novel test distribution. This is conventional reinforcement learning, not proof of self-organized native intelligence.

**Critical limitations:** This report does not establish independent immutable experiment/source custody, a sealed HOLDOUT, trained-baseline compute parity, an independently optimal online planner, ecological emergence or native Wingless/Yggdrasil integration. The fixed builder receives a strong hand-coded construction heuristic; it is therefore a legitimate upper-style behavioral reference but not a learned comparator. The local observation includes absolute position and goal-relative vector and may be richer than strictly egocentric sensing. Investigate that separately.

## Original identity (local only)

- Original isolated execution code: `/mnt/data/e_research/ed2/run_ed2.py`, SHA256 `fa4df4b975adb60d3a9a942f70872a5615272cb0333ebd334d472324a373062b`.
- Raw JSON: `/mnt/data/e_research/ed2/results.json`, SHA256 `717e7e3d548e5ade82f89724233b48fbbc712f06424fab2adbb286ef40d377e8`.
- Both files remain local outside this GitHub doc, so repository-only reproduction and FORGE FSA first-use are **not verified**.

## Next gate E-D3

Ablate coordinates/global goal direction, train a conventional agent with equivalent sample budget and evaluate a *separately specified* map family requiring two interventions, plus matched-visibility online search. Keep the original task success rate as a baseline and treat any transfer claim as provisional until source custody and a truly sealed independent test are available.

**Plain English:** A learning algorithm discovered building works in 19 of 36 reachable maps, but a simple prewritten rule solved every one. Promising task acquisition, not a breakthrough.
