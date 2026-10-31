# E Research E-D11 — local construction-transition learning ablation (2026-10-29)

**Actual execution:** engineering PASS, learned-mechanics *decision benefit NOT SUPPORTED*. Documentation-only advisory record; no FORGE autonomy, owner, model selection, native model, FSA first-use or scientific admission.

## Experiment

Actual original Python executable `/mnt/data/e_research/ed11/run_ed11.py` SHA-256 `48e3aa10c1d39f0057a0c22697171666f56e71dc4779b35e54b59b0ef45152bf`; original JSON `/mnt/data/e_research/ed11/results.json` SHA-256 `773d3c6c27a3e60564e1488ff3199d654976b029652e26bcbbc1f8a022ac5d6a`. Both files currently remain in local session storage, NOT included in this documentation-only GitHub commit, and executable depends on E-D8 sources also outside repository.

Collected 17,472 observation/action/outcome samples from source geometry: 15,792 legal moves, 1,680 legal builds. The empirical local predictor is extremely simple: it learns that a legal wall build removes an obstruction, while moves do not. This is **not** a learned forward world model or autonomous causal planner. All policies use the same locally exposed observation and legal actions, horizon 65, 110 energy units and 1–2 material units, same scripted merit function, with only the learned removal bonus varied. The 'reset' and 'scrambled' arms both remove the positive model bonus; they are *not meaningful independent scrambling strategies*. Critically, even with zero learned bonus the shared authored heuristic takes the same successful construction actions, so the designed ablation is **non-discriminating**.

Evaluation: three researcher-selected existing FIT shape families (horizontal, elbow and staggered), 12 new but unsealed development seeds per family (58000–58011), 3 repeated stochastic trials per seed, 5 arms = **540 trajectories**. No independent unfamiliar holdout. Exact rerun of all sample collection + trajectory results PASS. BFS verifies every world reachable. Energy/material nonnegative conserved by step-level assertions PASS. Wall time 0.226 s, process RSS peak 96,776 KiB (not independent CPU qualification).

| Policy | Horizontal success /36 | Elbow /36 | Staggered /36 |
|---|---:|---:|---:|
| Learned transition frequencies | 36 | 36 | 36 |
| Reset/no model | 36 | 36 | 36 |
| Scrambled/zeroed model frequencies | 36 | 36 | 36 |
| Optimistic conventional prior | 36 | 36 | 36 |
| Random | 1 | 2 | 2 |

Every nonrandom arm averages one build per trajectory, an indicator that the scripted control, not learned transitions, drives action selection. Correct prediction of immediate legal build consequences in source observations is a **mechanics classification result**, not proof of independently acquired environmental reasoning.

**Scientific decision:** reject any advantage claim from this experiment. Close this particular architecture/control comparison as uninformative about model utility. No FORGE science-acceptance, independently authenticated original source, sealed validation/holdout, matched learned model-based comparator, or native Wingless/Yggdrasil integration.

## Next eligible gate: E-D12

Design an **intervention-dependent decision fork** where the same locally observable barrier/action can lead to different delayed outcomes, learned from action-consequence interactions, and where the published heuristic demonstrably fails or picks the wrong build. Pre-register a *positive sensitivity test*: removing or scrambling a valid learned transition model **must measurably degrade** decisions, before interpreting any learned-model performance. Use equal budget, local observation, and a conventional model-based explorer as a trained baseline. Do not claim broad transfer before an authenticated original-source holdout.

**Plain English:** The agent learned a basic fact about construction, but it did not need that fact to solve the maze. The human-authored navigation rule solved it already; our test needs a scenario where learning actually matters.
