# E-D50 — environmental-observation ablation (2026-10-30)

**Execution PASS, scientific emergence or learning NOT DEMONSTRATED. Exploratory FIT, no sealed holdout.**

Reused E-C2 original source SHA-256 `1b3159224711ba46c4ef847fcce7ec1eff06ac6cd76e87d912461bf3cbe78154` and constructed a variant of the original episode function using a Python AST transformation. It replaced **policy-observed neighbor resource values** and the **policy's current-cell resource input** with a constant 0.2, without altering the resource dynamics or actual physical harvest. This is a **sensory-information ablation**, NOT an isolated learning-rule ablation. Seeds 33000–33011; 60 episodes: 12 each for evolutionary intact/blind and random-parent intact/blind; 12 for intact greedy. Original executable and raw result bytes are session-local and not independently stored or witnessed in the repository.

| Policy | Mean harvest/action | Median harvest/action | Median births |
|---|---:|---:|---:|
| Evolution, intact sensory information | 0.00730733 | 0.00675263 | 0 |
| Evolution, observation-blind | 0.00556187 | 0.00637371 | 0 |
| Random-parent, intact | 0.00419200 | 0.00402754 | 0 |
| Random-parent, observation-blind | 0.00334681 | 0.00348912 | 0 |
| Greedy intact | **0.03205475** | **0.03157589** | **6** |

For evolutionary policy, paired intact-minus-blind mean `+0.00174546`, **3 wins / 8 ties / 1 loss**. Random-parent intact-minus-blind mean `+0.00084519`, **3 / 8 / 1**. Evolution intact's mean was ~31.4% higher than its blind version, but tied most seeds and did not constitute robust evidence. Greedy achieved ~4.39× evolutionary intact harvesting.

Execution: two deterministic representative replay checks PASS; max energy-accounting residual `1.7151613462829118e-11`; exploratory script's wall runtime ~6.16 s. Reported 60 total episodes includes all arms, and no claim is made that all 60 were independently replayed.

**Disposition:** Source code is custom synthetic E-C2; no isolated online learning ablation, no locked original external environment, no independent holdout/witness, no verified GitHub custody for raw runs, no real native Wingless/Yggdrasil experiment. This remains advisory negative/ambiguous research evidence. Do not use as scientific first-use or FORGE autonomous model selection. Next meaningful gate: separate across-generation selection from observation use, using matched seeds and conventional baseline; do not claim emergent intelligence from a modest sensory benefit. DoorKey independent external runner blocker remains #1245.