# E-D52 — Exploratory transfer across resource-pattern families (2026-10-30)

**Execution PASS; competitive/generalizable native intelligence NOT DEMONSTRATED.**

## Protocol
Executed **108 exploratory episodes** (12 matched seeds 35000–35011 × 3 arms × 3 test families) using E-C2 synthetic ecology. The three pre-evaluation generations trained under **unchanged original dynamic resource-generation**. At evaluation only, replace resource center locations with (1) original dynamic three centers, (2) clustered stationary centers (2,2), (2,3), (3,2), or (3) sweeping deterministic centers varying with time. Policies compared: `evolve_dynamic`, `random_parent_dynamic`, `greedy_dynamic`. No reward/energy physics alteration; fitness policies have the original human-coded selection mechanism. These are newly chosen exploratory FIT conditions, **not independently sealed unfamiliar-family holdouts**. Original E-C2 source SHA256 `1b3159224711ba46c4ef847fcce7ec1eff06ac6cd76e87d912461bf3cbe78154`; E-D52 executed script SHA256 `d55a1041ca0a7e780b702d588da1387851e73110e3dece41345c21d06b73a13d`; result bytes SHA256 `9c8546feb4e0e7998cf76321bdd5f5f771760d58682070e1d1f3c70c5ce93ca7`. The script and complete raw bytes remain in session working files `/mnt/data/e_research/ed52`; those hashes are local identifiers, **not independent GitHub artifact custody**.

## Observations (mean harvested resource per action)
| Test resource family | Evolve fitness | Random parent | Greedy control |
| --- | ---: | ---: | ---: |
| Original dynamic | 0.0122946381 | 0.0040313602 | **0.0326431550** |
| Clustered stationary | 0.0096269946 | 0.0041495814 | **0.0360170610** |
| Sweeping dynamic | 0.0121310194 | 0.0042083159 | **0.0291505206** |

Paired fitness-selected minus random-parent: original +0.00826328, clustered +0.00547741, sweeping +0.00792270; **10/0/2 wins/ties/losses in every condition**. Fitness-selected minus greedy: original -0.02034852, clustered -0.02639007, sweeping -0.01701950; **1/0/11** in every condition (greedy wins 11 of 12). Max within-episode energy-accounting residual `2.1714186004828662e-11`. Representative deterministic replays **3/3 PASS**. The 108 trajectories were not all independently replayed. Wall runtime ~9.955 seconds.

## Interpretation
Measured effect of fitness selection persists across two manually constructed alternative environmental resource topologies. But selection was human-coded, models were not frozen and retested by an independent witness, **no conventional trained agent** was compared, and greedy remains overwhelmingly superior in all test families. The experiment does not show online learning, independent causal inference, meaningful unfamiliar-task transfer or emergent intelligence. Do not promote into native Wingless/Yggdrasil or FORGE model selection. Keep scientific-first-use blocked.

Next meaningful research qualification: preserve the **actual executable and raw bytes in content-addressed repository evidence**, then independently sample a truly unfamiliar environment family with trained conventional controls. Existing official DoorKey execution remains separately blocked under issue #1245. No FORGE autonomy changes.