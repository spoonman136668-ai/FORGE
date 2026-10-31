# E-D51 — Matched selection × sensory ablation (2026-10-30)

**Execution PASS; scientific learning/generalization NOT demonstrated.** Real exploratory local execution on the E-C2 custom synthetic ecology, 12 new FIT-extension seeds 34000–34011, 5 arms per seed (60 trajectories). No sealed holdout, independently authenticated artifact custody, native Wingless/Yggdrasil or original upstream external benchmark.

## Design
2 × 2: `fitness-selected` vs `random-parent` across intact observations vs observation-blind policy (neighbor and current-cell policy resource observations replaced with constant 0.2); plus original intact greedy controller. Kept ecological physics and harvested energy accounting intact. Existing E-C2 source SHA-256: `1b3159224711ba46c4ef847fcce7ec1eff06ac6cd76e87d912461bf3cbe78154`. Executed script local SHA-256 `9915d0fb6f644e2ad170c3df0f3c6c392765766448b135fc19df2f1864a1c68a`; raw JSON SHA-256 `d27021a5986d8d57d76e10cc3d78593ba69d3fa6af3a98f1513bdf70f8a48197`. Raw bytes and script are session-local, not authenticated or stored in GitHub by this advisory record.

## Measured results
| Arm | Mean harvested resource per action |
| --- | ---: |
| fitness + intact | 0.0154288262 |
| fitness + blind | 0.0062909391 |
| random parent + intact | 0.0069613449 |
| random parent + blind | 0.0041435142 |
| greedy intact | **0.0316958587** |

Paired fitness minus random (intact): **+0.0084674813**, wins/ties/losses **8/2/2**. Paired fitness minus random (blind): **+0.0021474248**, **9/3/0**. Observation intact minus blind within fitness: **+0.0091378872**, **6/6/0**. Within random-parent: **+0.0028178307**, **4/7/1**. Exploratory difference-in-differences mean `+0.0063200565`, median `0`. Fitness+intact minus greedy mean **-0.0162670325**, paired wins/ties/losses **2/0/10**, greedy ~2.05× mean resource/action.

Within-episode energy-accounting max residual `1.620725775808296e-11`. Representative deterministic replay checks **4/4 PASS**; not all 60 were rerun. Runtime about 5.7 sec.

## Interpretation and limits
Fitness-selected parent sampling has **some measured benefit over random-parent controls in this synthetic FIT extension**; observing environmental resources also affects performance. Effects vary with seed and show ties and losses. The model's selection and observation rules are explicitly human-coded, not novel autonomous learning; this is **not** a causal identification of learned internal mechanisms or unfamiliar-family transfer. Most importantly, the hand-designed greedy baseline remains substantially stronger (wins 10/12). Reject any competitive-emergence or learning breakthrough claim.

**Next useful scientific gate:** hold out distinct resource-generation mechanisms/environments, freeze policy and selection choices, add stronger conventional learning baselines, and publish original executable/raw result bytes under independent custody before scientific first-use. Continue keeping official DoorKey execution blocker #1245 separate. Do not alter FORGE owner/autonomy/controller or native model selection.
