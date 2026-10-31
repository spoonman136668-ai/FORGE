# E Research E-D18 — nonstationary probe acquisition FIT (2026-10-29)

**Isolated engineering PASS; beneficial reliable adaptation to changing information quality NOT SUPPORTED.** Original experiment executed; advisory only; no FORGE autonomy, controller, native model, research admission or scientific first-use claims.

## Experiment executed

Standalone local Python simulator (not imported from previous E-D modules), 16 development seeds × 360 sequential trials × 8 policies = **46,080 evaluated episodes**, with exact full rerun match (PASS). Public task: one binary hidden change after the first automatically successful barrier stage, followed by second paid intervention. Agents decide whether to buy no observation, probe A (1 energy), or probe B (3 energy); two fixed intervention charges total 8 energy, harvest 12 only for correct final intervention. Starting energy 20, material 2; accounting checked on every episode. Critically, the **first intervention is pre-solved**, not learned; the experiment isolates information acquisition. When a probe is selected, its binary signal is observed; post-choice feedback reveals whether that probe was correct, so reliability can be learned *after*, not before, the decision. No probe observations yield no probe accuracy training. Each episode's underlying flip and probe outcomes are deterministic per seed/time and identical across compared agents.

Hidden physics regimes: episodes 0–179 probe A reliability .85 and B .60; episodes 180–359 A reliability .55 and B .90. The change point is known only to generator; agents are not told it or the accuracies. Candidate strategies: (1) **sliding empirical VOI** with last 48 selected-probe observations and a *handcoded* VOI formula, (2) standard Beta posterior plug-in VOI (nonexploratory), (3) Beta Thompson exploration with the same VOI expression, (4) optimistic UCB with sliding 48 observations, (5) privileged oracle given true accuracies as an **upper bound**, (6) always probe A, (7) never probe, (8) random selection. All policies have identical public costs and feedback, except privileged oracle; their chosen probes change the subsequent learning data. Mean net = reward − (8 + chosen probe cost).

| Policy | Total success /5760 | Probe A | Probe B | Mean net |
|---|---:|---:|---:|---:|
| Sliding empirical VOI | 2912 | 0 | 0 | -1.93333 |
| Beta plug-in VOI | 2912 | 0 | 0 | -1.93333 |
| Thompson Beta | 4104 | 5373 | 355 | -0.56771 |
| Optimistic UCB | 4344 | 4896 | 864 | **-0.25000** |
| Known-reliability oracle | 5056 | 2880 | 2880 | +0.53333 |
| Always A | 4016 | 5760 | 0 | -0.63333 |
| Never probe | 2912 | 0 | 0 | -1.93333 |
| Random | 3789 | 1936 | 1895 | -1.42934 |

After the unannounced regime change, UCB purchased the now-favorable probe B in **864/2880** opportunities; Thompson in **280/2880**, versus privileged oracle **2880/2880**. UCB achieved late mean net **-1.65833**, oracle **-0.09167**. These are reused development seeds, not independent first-use science. The naive plug-in policies *never explore* and fail even the initial regime; this is an information-acquisition bootstrap failure, not a disproof of Bayesian learning.

### Scientific limits / implementation hazards

- Only 2 probe options and a binary change; the correct first barrier decision and reward mapping are pre-specified. Not a native emergent intelligence architecture, world-model learner, general environment or lineage simulation.
- UCB uses a handcrafted optimism bonus; Thompson uses ordinary Bayesian sampling. No novel cognitive mechanism or superiority to strong conventional controls.
- There are 16 independent world seeds with 360 time-correlated episodes each; counts of episodes **must not** be treated as 46,080 independent worlds. No inferential confidence intervals.
- Agents use binary signal as stated without attempting to invert below-chance sources; all true probe reliabilities are >.5.
- No independently authored unknown-change-point comparator, no explicit change-point detection, no independent seeded holdout, no authenticated FORGE CI/FSA reproduction, and no CPU/energy efficiency measurement beyond Python process execution.
- The original source and results are local session files and **not** in this documentation-only GitHub commit.

Original executed `/mnt/data/e_research/ed18/run_ed18.py` SHA256 `14b3d33d559eee75e84841354c9d829c2bbe9ca731f0067f949988069b5f8bd`.
Original JSON `/mnt/data/e_research/ed18/results.json` SHA256 `367b03d9d99db9c96bf8b4528198b479317755affc5a0abeacfcc66e78ee25fd`.

**Decision:** The best nonoracle control remains behind the privileged reference and fails to reliably shift probe usage after a regime change. No advancement to native model selection. **Next E-D19:** audit change-point detection and sample efficiency using a conventional sliding-window UCB / discounted Thompson / CUSUM Bayesian baseline under matched costs; freeze an independent reliability-shift schedule and evaluate recovery latency, postchange regret and per-seed uncertainty. Do not add architecture complexity until conventional nonstationary baselines have been qualified.

**Plain English:** The agent can explore costly clues but gets stuck using the old clue after the world changes. Standard exploration helped, yet did not reliably catch up.
