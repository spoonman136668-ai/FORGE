# E Research E-D15 — online second-intervention replanning FIT (2026-10-29)

**Isolated engineering PASS; decision-relevant observed environmental changes SUPPORTED in FIT; superiority to conventional history-aware learning NOT SUPPORTED.** Documentation-only advisory. No FORGE autonomy, owner, controller, queue, native model, selection or science-admission changes.

## Experiment performed
Executed a standalone Python 2-gate delayed-resource environment. The agent observes a binary cue and first-gate orientation, pays 4 energy/1 material for first intervention, then a stochastic independent structural flip (environment-only draw) is revealed before the second gate. Second correct choice depends on cue, second orientation and the newly revealed flip. A second paid intervention costs another 4 energy/1 material. After two scripted traversal steps the agent receives 12 harvest only if both openings were correct. No intrinsic reward for building. Initial energy 20, material 2, with exact conservation assertions.

Trained empirical local action/consequence records from 2,000 randomized two-stage episodes (training seeds 91000–92999), all 24 action/outcome context cells supported by >=49 samples. The first-stage consequence is observed and the second-stage outcome is only attributed when the first was passable, avoiding second-stage target oracle. Evaluated 240 unsealed development worlds (94000–94239) x 7 policies = **1,680 evaluations**, exact full-result replay PASS. Policies: online adaptation from learned table, conventional same-information contextual table, cached pre-change plan that assumes no flip, flipped/scrambled change observation, model-free random reset, random and fixed-first. Same physical intervention costs, observations except specified ablation, and nominal decision opportunities. All energy/material assertions PASS. Local execution wall ~0.06882 sec, process RSS peak 98060 KiB (session-wide, not independent qualification).

| Policy | Successful /240 | Mean harvest minus 8 energy cost | On structural-change worlds /125 |
|---|---:|---:|---:|
| Learned consequence lookup with online second decision | 240 | +4 | 125 |
| Conventional history-aware learner | 240 | +4 | 125 |
| Cached initial plan, ignores new flip | 115 | -2.25 | 0 |
| Scrambled change cue | 0 | -8 | 0 |
| No retained model (random reset) | 67 | -4.65 | 33 |
| Random | 53 | -5.35 | 28 |
| Fixed-left | 69 | -4.55 | 33 |

**Scientific interpretation:** The first intervention is acted before environmental change is observed; later correction is essential and the cached-plan control fails exactly when the structural flip occurs. This supports **decision-level sensitivity to new observations**. Nevertheless both successful policies use equivalent finite contextual consequence tables learned from the same intervention records. A binary flip is directly observed; there is no learned latent transition model, uncertain-information planning, new world family, native Wingless/Yggdrasil architecture, or independent scientific first-use. Delayed traversal is still scripted. The test is a **conditional two-decision adaptation**, not robust general causal planning.

**Original isolated local source:** `/mnt/data/e_research/ed15/run_ed15.py` SHA256 `fd62555829a54be7a41fb67afb222e6ae8d0d371c5bf38545e8f02907da08349`.
**Original raw JSON:** `/mnt/data/e_research/ed15/results.json` SHA256 `82992aa83801afa07ef5ee23b40c7f33ceb5cc531ee64b20cf7b0587b04d91a4`.
Original executable/results are NOT in this docs-only commit and not independently authenticated by FORGE CI/FSA; repository-only reproduction and scientific acceptance UNVERIFIED.

**Next E-D16:** Make structural change *latent and only partially observed* through action-conditioned probes with explicit energy/time costs; compare belief-state Bayesian conventional control against episodic and learned-transition approaches, fixed observation/action budgets, correct posterior updates and no oracle; establish a blinded unfamiliar mechanism-family protocol before claiming generalization.

**Plain English:** The agent changes its second construction choice when the world changes, and that matters. A standard learner can do it equally well, so this is a useful test result, not a breakthrough.
