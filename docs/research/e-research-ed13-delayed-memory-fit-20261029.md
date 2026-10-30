# E Research E-D13 — delayed observation memory FIT (2026-10-29)

**Engineering PASS. Memory-dependence positive; advantage beyond conventional history-aware learning NOT SUPPORTED; multistep causal planning UNTESTED.** FORGE advisory only; no controller, autonomy, native model, research selection or scientific admission changes.

## Actual new CPU execution

Standalone original local code: `/mnt/data/e_research/ed13/run_ed13.py` SHA256 `9410117262499c3b6ce5028840640df5e7d766fec7b9ea4588b70cae0714b65b`.
Original machine-readable JSON: `/mnt/data/e_research/ed13/results.json` SHA256 `e90fd5af40b2a12df74f3aa69ed8cd382353f0e882596c6173de93dbf83d3a70`.
**These originals remain outside this GitHub documentation-only commit; repository-only reproduction and FSA first-use custody UNVERIFIED.**

Environment is a simplified **delayed-context two-gate intervention** derived conceptually from E-D12: the initial binary cue arrives at t0; independent distractors at t1/t2; observed gate orientation at t3; the agent spends 4 energy and one material to open one of two gates; two automatic traversals follow before +10 harvest if the opened chamber contains food. The generator hides a stable cue-orientation-to-target relation from agents; reward for construction alone is zero. Agents cannot see the target or entire world at decision time, and no agent receives the underlying mapping. The two traversal steps are **scripted rather than controlled decisions**, therefore this is **not genuine multi-step planning**.

Training 480 randomized intervention episodes (seeds 71000–71479) with every cue/orientation/action context represented >=35 times. Evaluation 120 new but unsealed development seeds 72000–72119 × five variants = **600** trajectories. Variants: empirical episodic context/action reward table, identically trained standard history-aware contextual table, cue discarded (stateless), cue inverted (scrambled memory) and random action (reset). Same public observations, training examples, identical action cost and budget. Per-trial energy+cost and remaining-material+spent conservation PASS, no negative resource, and exact replay of all evaluation trajectories PASS. Script wall ~0.024s, peak process RSS 96144 KiB (process-level, not independently qualified).

| Policy | Successes /120 | Mean net (reward minus 4 energy cost) |
|---|---:|---:|
| Episodic memory | 120 | 6 |
| Conventional history-aware learner | 120 | 6 |
| Stateless | 59 | 0.9167 |
| Scrambled cue | 0 | -4 |
| Random reset | 54 | 0.5 |

**Interpretation:** remembering an earlier cue materially affects later intervention choice, as shown by cue-scrambling and cue-discard controls. But the episodic and conventional learners are functionally the same empirical lookup and tie in outcomes. The world has four public contexts and two possible actions: trivial finite lookup is sufficient. There is no learned transition dynamics, causal compositional reuse, or new intelligence. The generator's stable deterministic cue mapping is intentionally easy. New evaluation seeds are not sealed out-of-family scientific holdout.

**Next E-D14:** implement actual agent-controlled 2+ intervention sequence with delayed action-conditioned consequences, resource/visibility budgets, and a conventional Bayesian/model-based history learner. Predeclare a model-sensitivity test, decision-level traces, matched interaction/search budgets, and new mechanism-family validation. Distinguish ordinary table memory from transferable causal structure before proposing native Wingless/Yggdrasil use.

**Plain English:** Remembering an early clue is useful when the decision comes later. Standard learning already does it perfectly, so this is not evidence of a new intelligence architecture.
