# E Research E-D9 — empirical local transition model vs episodic lookup FIT (2026-10-29)

**Engineering PASS; independently learned causal strategy NOT ESTABLISHED.** Original Python was executed in isolated local container, not through FORGE CI or sealed FSA. No FORGE owner, runtime, controller, autonomous schedule, native model, science admission or selection changes.

## Execution and controls

Inherited E-D8 9×9 two-dimensional environments (horizontal barrier, elbow and staggered), legal actions, physical construction costs, observation representation and source episodic memory. Existing source Q training: 1560 single-wall FIT episodes; source-memory collection: 144 double-wall attempts and 109 retained source-memory observation keys. This gate additionally gathered **2040** local state/action/next-state examples from single vertical-wall source scenes and fitted per-action empirical progress and immediate wall-removal frequency. Each of four build orientations had >50 examples and observed 100% immediate adjacent wall removal when legal.

A new **model-guided** agent used those empirical removal frequencies, with a *manually specified one-step goal-distance heuristic and bonus for clearing a wall toward the goal*. It is thus a **hybrid learned-dynamics/hand-coded action rule**, not a fully learned planner, an independent discovery of causal rewards or an optimized model-based conventional baseline.

Same goal, seed, 65-action budget, 110 energy and local action-material restrictions for all evaluated policies. 18 reused FIT seeds per shape x 4 stochastic repeats x 5 agents (model-guided, frozen source episodic-memory, empty episodic-memory, random, programmed builder) = **1080 evaluation trajectories**. Explicit independent BFS oracle established that all test worlds are reachable, but its output never entered any agent. Cost ledger and exact full seeded replay PASS.

| Target layout | Model-guided /72 | Episodic source /72 | Empty memory /72 | Random /72 | Programmed builder /72 |
|---|---:|---:|---:|---:|---:|
| Horizontal | 72 | 7 | 2 | 6 | 72 |
| Elbow | 0 | 2 | 0 | 1 | 0 |
| Staggered | 72 | 5 | 1 | 3 | 72 |

**Decision:** The hybrid policy reliably solves two specific unseen physical configurations but is functionally equivalent in outcome to the already successful programmed builder. Both fail the elbow, illustrating the limits of locally greedy planning and potential conflict between immediate goal progress and eventual reachability. Construction-removal physics itself is provided by training examples, but *the decision to remove forward wall obstructions is explicitly authored*. Consequently no claim of autonomous causal invention, compositional planning, general intelligence, or native Wingless/Yggdrasil advancement is warranted. Compare **strong conventional model-based explorer** and truly learned policy with equal data access in later work.

**Scientific restrictions:** FIT worlds are reused and not independently held out. Training mechanical examples are off-policy samples generated from the source's complete state but agent action decisions use only local observation. Empirical action transitions were summarized by action orientation rather than a general identifiable learned transition model; planning prior was manually authored. No matched trained model-based baseline, separate source authentication, uncertainty estimate, FSA first-use or independent scientific witness.

**Local original bytes (NOT committed here):**
- `/mnt/data/e_research/ed9/run_ed9.py` SHA256 `e9e175f5d0dbea186bddfacee701a220b0492493cd7e1b88b863acc7d49e63c0`.
- `/mnt/data/e_research/ed9/results.json` SHA256 `422e7afbade8007d5a8ff2b7b67516dd44a31b1d0e4cc65470b6e052c5c28dde`.

**Next E-D10:** Build an episodic causal graph that learns action-conditioned transitions and plans multi-step paths from observations with a defined exploration budget; compare it to a conventional budget-matched model-based explorer, the existing hybrid, and episodic retrieval, particularly on the elbow family. Explicitly track which priors, map data, and planner computations are handcoded; fail if a solver receives hidden layout.

**Plain English:** Learning what building does helps when a simple greedy strategy is enough. It still doesn't solve corners, and a human-designed decision rule did most of the work.
