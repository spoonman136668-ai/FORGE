# E Research E-D5 — persistent Q-memory diagnosis (2026-10-29)

**Status:** Isolated FIT numerical execution and full seeded replay PASS. Persistent learning improvement **NOT SUPPORTED**. Causal attribution of failure to state aliasing **UNVERIFIED**. Research advisory only; no FORGE owner, autonomy, controller, or native model modifications.

## Actual experiment

Reused E-D4 Q trainer, E-D3 reduced observation and two-wall 9x9 world, same six single-barrier training seeds and 12 two-barrier evaluation world seeds. Ran 1560 single-wall Q-training episodes, then 12 repeated encounters for each of 12 worlds and three policies: persistent online Q with exploration, pre-trained Q reset after each encounter with identical exploration, and a transparent hand-coded one-step local causal controller. **432 evaluation trajectories** (12 × 12 × 3). Maximum decision horizon and energy/material costs are identical. The deterministic causal controller selects legal adjacent wall removal in the goal direction; it does **not** learn and is **not** a matched-trainable model-based learner. Original E-D4's fixed builder shows similar results and is not independent confirmation.

| Policy | trials 1–3 / 36 | trials 4–6 / 36 | trials 7–9 / 36 | trials 10–12 / 36 |
|---|---:|---:|---:|---:|
| Persistent updating Q | 7 | 2 | 1 | 3 |
| Reset-after-trial Q (same exploration) | 7 | 8 | 7 | 9 |
| Hand-coded local causal control | 36 | 36 | 36 | 36 |

**Representation diagnostic:** Across the 12 evaluation environments, 84 distinct reduced observations were formed by scanning possible walkable positions with the initial unchanged map. Of those, 70 observations map to multiple world/position combinations (maximum 20 combinations per reduced state). This demonstrates **state aliasing**, but not conclusively that aliasing causes poor TD learning. Across adaptation attempts, the persistent Q learner changed mean 28.1319 state/action entries; pretrained Q has 351 entries, increasing to an average 422.4167 entries after trial 12, with last-trial max absolute value 29.92. The table growth does not itself establish catastrophic forgetting; old-Q vs new-Q performance ablation is required.

**Accounting and validity:** Simulation energy/material conservation asserts PASS; independent seeded Q training and *all 432 evaluation record* exact replay PASS. Same 65-step agent budget. Worlds reused FIT/development, not sealed holdout. No model-free/model-based *learning* parity, no test of memory ablation that retains observation but suppresses TD updates separately from exploration, no independent scientific acceptance.

**Original source and raw JSON (not in this docs-only commit):**
- `/mnt/data/e_research/ed5/run_ed5.py`, SHA-256 `5d5ce4b74280377cd29979ba18f8a5b67ef86b9f90c83e348fb6f06817b6ba1f`
- `/mnt/data/e_research/ed5/results.json`, SHA-256 `dd630c92c7bb4da1844ec7a8050ef25217acc3e30037fd4681dcd407a482c527`

**Next E-D6:** isolate aliasing with a paired full-Markov-state versus aliased-state Q ablation under identical training, exploration and evaluation seeds; compare explicit episodic memory with equivalent local observations and update budgets. Test whether reliable two-barrier transfer emerges without privileged map coordinates or scripted construction actions. Predeclare negative and positive controls, never claim scientific first-use without original authenticated source and holdout.

**Plain English:** The learner's reduced memory representation merges many different situations. Its updates did not improve success, while a written rule solves the task. We know the representation is ambiguous, but not yet exactly why the learning fails.
