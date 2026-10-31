# E-D61 — Always-harvest conventional control (2026-10-30)

**Executed in isolated local synthetic E-C2 ecology. Engineering PASS; novel learning/competitive intelligence NOT DEMONSTRATED.**

Design: E-C2 ecology with original energy accounting and per-cell resource regeneration, 12 fresh exploratory FIT seeds 36000–36011, 4 arms/seed (48 episodes). New conventional heuristic **always harvest** removes navigation decisions; greedy navigates only to richer neighbors, fitness-selected evolution and random-parent evolution retain their old mechanics. Original E-C2 source SHA-256 `1b3159224711ba46c4ef847fcce7ec1eff06ac6cd76e87d912461bf3cbe78154`. The actual new test script is local and is not independently qualified or retained in GitHub. Test used an AST-generated alternative `episode` function only for the new control; no change to environment physics or energy ledger.

| Arm | Mean harvest/action |
|---|---:|
| Fitness-selected evolution | 0.01402199416 |
| Random-parent evolution | 0.00407776177 |
| Greedy heuristic | **0.03186322806** |
| Always-harvest heuristic | 0.00657981727 |

Greedy minus fitness-selected mean `+0.01784123390`; paired wins/ties/losses **10/0/2**. Always-harvest minus fitness-selected mean `-0.00744217689`; paired **2/6/4**. Random-parent minus fitness-selected mean `-0.00994423239`; paired **0/1/11**. Representative deterministic replay PASS; maximum within-episode energy accounting residual `1.6262546864709293e-11`. Local runtime ~4.26 sec.

**Interpretation:** A crude always-harvest reflex does not explain greedy's advantage. Spatially informed greedy choice remains substantially stronger than fitted evolution; the apparent selection effect vs random-parent does not meet independent scientific standards. There was no native Wingless/Yggdrasil training, truly unfamiliar benchmark, sealed holdout or independent witness.

**Custody:** local raw run and script are inspectable in the current session under `/mnt/data/e_research/ed61/`, but this file records summary only. Do not misrepresent local evidence as authenticated original GitHub bytes. E-D52 evidence custody and official DoorKey remote execution remain outstanding. No FORGE production changes.
