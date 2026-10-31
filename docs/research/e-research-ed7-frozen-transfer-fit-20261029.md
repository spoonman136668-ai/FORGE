# E Research E-D7 — frozen episodic memory transfer FIT (2026-10-29)

**Engineering PASS; limited cross-layout experience reuse observed in FIT; independent scientific generalization UNVERIFIED.** No FORGE autonomous-control, model-selection, native-model or scientific-admission changes.

## Actually executed
Reused original E-D3/E-D6 tabular Q and local observation/energy/material simulator. Trained reduced-observation Q on single-wall family (six previously used development seeds × 260 = **1,560 episodes**). Collected successful local observation/action choices into one episodic dictionary from **144** encounters with original two-wall source worlds (12 source seeds × 12 attempts). Source-memory keys: **109**; successful source attempts: **101**. Memory is copied and frozen for all target evaluations, with **no target outcome changes carried into later tests**.

Targets are three *design-selected* modifications of barrier x-coordinates to the source two-wall 9×9 grid: **near** (x=2,5), **wide** (x=2,6), **triple** (x=2,4,6). All still share wall mechanics and goal structure. Each mode has 18 new but **unsealed FIT/development** random seeds 55000–55017 × four stochastic repetitions × six policies = **1,296 evaluation trajectories**. Policies: frozen source-memory Q with epsilon .25, empty-memory Q with identical epsilon and base Q, scrambled-memory Q, frozen Q without memory with epsilon .25, no-building greedy, and hand-coded builder. Every policy has same nominal 65-step, 110-energy action limit with one material per wall, build cost 4 energy vs movement 1, and resource reward only at goal. Preprogrammed builder has a crafted construction heuristic and is not a trained comparator. The four repetitions of each seed are **not independent environment instances**.

| New layout | Source memory /72 | Empty memory /72 | Scrambled memory /72 | Fixed builder /72 | Greedy /72 |
|---|---:|---:|---:|---:|---:|
| Near (2,5) | 41 | 5 | 0 | 72 | 0 |
| Wide (2,6) | 12 | 3 | 0 | 72 | 0 |
| Triple (2,4,6) | 2 | 1 | 1 | 72 | 0 |

BFS verifies all target worlds solvable. Invariant assertions on energy spent, material conservation and nonnegative state PASS. Exact reproduction of entire training/source-memory/evaluation result **PASS**. Execution 2.99 seconds, peak process RSS 100496 KiB.

## Interpretation and limitations
The trained frozen local episodic memory improves performance relative to empty memory on *some* altered barrier layouts, notably near-spacing. It almost never solves the 3-barrier task. The source memorization precedes all target tests, avoiding same-target repeated-learning contamination seen in E-D6. This is **suggestive transfer by exact matching of local reduced observations**, not proof of learning reusable causality, systematic compositional generalization or general intelligence. Near and wide worlds are still the same wall mechanics and task family. A cross-family transfer test, independent held-out environmental generator, true model-based trained baseline, information-equivalent trained control, repeated training seeds and uncertainty intervals remain pending. Report is based on FIT seeds, not sealed first-use.

## Original-byte identity / custody
- Local Python source: `/mnt/data/e_research/ed7/run_ed7.py` SHA-256 `56ec02aca000cdcfb680a6ae121bc74e541773ddea9ec1b384145d406b7f5994`.
- Local result JSON: `/mnt/data/e_research/ed7/results.json` SHA-256 `e23e17f4fc9a05d11693c9c247e5f53743bade51a4ff1610e50dad2d26091ff1`.
- Original source depends on E-D6 and E-D3 modules that remain isolated-local. These bytes are **not committed** by this docs-only GitHub record. Source hashes alone do not constitute authenticated FORGE FSA custody, CI, or independently qualified scientific acceptance.

**Next E-D8:** Test whether successful experience compresses into a generalized construction rule, versus exact-context lookup. Predefine out-of-family wall orientations (horizontal, L-shaped, staggered) with identical local observations/actions; compare transferred episodic memory, explicit learned local transition model, learned model-free baseline and scripted reference under matched training opportunity, wall material and decision budgets. Failure or low sample efficiency should be recorded without hyperparameter tuning on held-out outcomes.

**Plain English:** Remembered experience helped on some rearranged walls, but not three barriers. We have evidence of narrow reuse, not broad generalization.
