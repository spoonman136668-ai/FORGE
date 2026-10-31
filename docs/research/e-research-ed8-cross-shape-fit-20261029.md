# E Research E-D8 — cross-shape FIT transfer (2026-10-29)

**Engineering PASS; broad cross-shape transfer NOT SUPPORTED; scientific qualification UNVERIFIED.** Original-source and raw bytes remain local, outside this documentation-only FORGE advisory commit. No controller, owner, autonomous scheduling, native model, selection, or science-admission changes.

Ran actual local Python experiment derived from E-D7/E-D6/E-D3. Single-wall source Q-training 1560 episodes, 144 two-wall source collection attempts; resulting frozen successful-trace episodic memory 109 keys, source successes 101, base Q entries 351. Evaluation: 3 new shape families (horizontal wall, elbow, staggered barriers), 18 unsealed FIT world seeds 56000–56017, four stochastic attempts each, six policies = **1296 evaluation trajectories**. Original source memories frozen across all target evaluations; exact local reduced-observation lookup, same 65-step/110-energy budget, 1 or 2 material units depending on barrier family; construction costs 4 energy and 1 material, no construction reward. Offline BFS confirms every test world's reachability, never fed to policy. All per-step budget assertions and exact whole-experiment seeded replay PASS.

| Target shape | Frozen source memory /72 | Empty memory /72 | Scrambled memory /72 | Random /72 | Greedy nonbuilder /72 | Scripted local builder /72 |
|---|---:|---:|---:|---:|---:|---:|
| Horizontal | 7 | 2 | 1 | 6 | 0 | 72 |
| Elbow | 2 | 0 | 4 | 1 | 0 | 0 |
| Staggered | 5 | 1 | 2 | 3 | 0 | 72 |

The frozen policy's apparent advantage over empty memory is small and its absolute task success is poor. Its elbow result is worse than scrambled memory. This does **not** support generalized causal reasoning or reliable out-of-family transfer. The scripted local builder fails the elbow shape, so it is not a universal planner; the evaluator-only BFS identifies feasible paths. Development geometry is researcher selected, not blinded, and four attempts per world do not provide independent environmental replicates. No learned model-based agent or matched training-compute conventional exploration comparator was implemented at this gate.

Local executable `/mnt/data/e_research/ed8/run_ed8.py`, SHA256 `996816764cd10518e76cdcbead8667fdb7fbba1f8ba92c8dd503b6e4d2641bae`; raw `/mnt/data/e_research/ed8/results.json`, SHA256 `5188bbcc90b501e71d8fcf2f63687ac2f74d0e0b63d27cd5dc0beddc0946c599`. Source imports previous local code. This advisory summary does not contain independently reproducible original science, immutable source custody, a sealed holdout or an independent scientific witness. Resource reporting: isolated wall ~1.818 sec, process RSS peak 98076 KiB.

**Next E-D9:** implement a local-observation learned transition model or structured episodic causal mechanism; compare with equal-access and fixed interaction budget against the same experience-memory agent plus a genuine conventional model-based explorer on predeclared FIT variants. Close this representation if it cannot exceed exact-observation retrieval on unfamiliar shapes.

**Plain English:** Remembering prior successes barely helps when the wall shapes really change. The agent has not yet learned a general principle of environmental modification.