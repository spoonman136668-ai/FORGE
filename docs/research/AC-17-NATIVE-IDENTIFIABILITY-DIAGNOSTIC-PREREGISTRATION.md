# AC-17 — Predeclared negative-source identifiability and native-locality diagnosis

**Gate scope:** Diagnose AC-16 against authentic public DTR source, without new DTR episodes, new learner architecture, controller changes, or protected scientific first-use. This is **development only**; existing science admission stays NO-GO.

## Frozen antecedents

- AC-16 executable qualification on Windows + Linux: commit `431ccb21ee3cd2bc989e1a52f8ec667a5432d2be`, [run #40793254797](https://github.com/spoonman136668-ai/FORGE/actions/runs/40793254797). AC-16 current native Yggdrasil active branch `92c421a5475a27015a390efb88c373eb5f15379d`, Git blobs of original `src/yggdrasil/nca.py` (`7b15017b7f5c6f9b507bcf43f4545a3c972f40d1`) and `training.py` (`af610c4334d2dd16415b39dd344ae2ed82ddd931`).
- Unchanged upstream Causal-Gymnasium DTR `c94e9a4cd3641588b6b8507e71ccee5c27032bdf`; 8 public FIT episodes / 16 action/outcomes, 4 public DEV episodes / 8 outcomes, original source-only permissibility verified in AC-15. AC-17 **reuses exact same authenticated records** from same CI run; zero new source-owned episodes. DEV used only once to score already frozen original AC-16 and diagnostics, never for updates or selection.
- Prior AC-16 native model trained via **external supervised BCE loss**, not original Ygg morphology objective, and lost to contextual tabular and pooled conventional controls: 3/8 DEV correct, Brier .42475 vs tabular .32382 and pooled .23920; rotated FIT-label negative also better on eight outcomes. Retain this negative.
- Current FORGE issue [#1031](https://github.com/spoonman136668-ai/FORGE/issues/1031) records **six exact initial-parameter action-local feature collisions** in a distinct synthetic Yggdrasil eight-cell prototype and a negative-only reward-credit failure. These results are **not automatically attributable to the AC-16 current NCA**. AC-17 explicitly tests rather than asserting a common cause; no steering into F139 without an independently qualified manifest/owner decision.

## Frozen diagnostic questions

1. **Public information sufficiency:** Count each unique FIT `(stage, observation, scripted action)` triple; for each count binary source outcomes and identify directly conflicting outcomes for *identical public input*. Count unseen DEV contexts/arms, FIT majority irreducible mistakes and conditional entropy. Same exact public input with both outcomes is direct finite-sample ambiguity (could reflect stochasticity/hidden context); **not proof of latent confounding or a mathematical global impossibility**. Label collisions are sourced from authentic public outcomes.
2. **Out-of-episode test, not DEV tuning:** Predeclare **eight leave-one-FIT-episode-out folds** (7 FIT source episodes, 1 excluded episode), each re-initializing the exact original NCA with fixed seed `20261028`, same 64 Adam steps and same public spatial encoding. Evaluate excluded episode's two outcomes once. Match each fold to **fully fitted contextual tabular Laplace and pooled fitted prior** on precisely the same 14 FIT outcomes. Report fold Brier/accuracy and all eight fixed fold assignments. These are *cross-validation diagnostics on public FIT*, not new unbiased unfamiliar-family evidence or a reason to select another model on DEV.
3. **Native spatial sensitivity, not environment counterfactual:** Retrain the same pinned NCA once on full 16 FIT public outcomes, without access to DEV labels; compare predictions on the eight DEV public inputs against isolated flips of **stage**, **observation**, **action** bits in the spatial encoder. Record mean and max change and exact unchanged cases for each. This probes *model-input feature sensitivity* only, **not** the upstream `ctf_do` API or the consequences of alternate physical actions; never claim causal action effects from these flips.
4. **Memory and locality boundary:** Retain the original native NCA's frozen state-dict checkpoint/cold restore guarantee from AC-16. Do not call it independent-cell persistent plasticity or world-memory retention, because its weights are shared and the preexisting `training.py` is morphology-specific. Record whether current verified source offers a native binary DTR `observe(action,outcome)` interface: **it does not**. We must not substitute the legacy `PublicCausalCells` for the active native local NCA.

## Resource and admissibility

Use the same authenticated source/CPU PyTorch venv and pinned current Ygg source from AC-16 in GitHub-hosted Linux/Windows PR workflow, so no further DTR episodes beyond the AC-15 parent. Explicitly cap additional native training to eight 14-example folds + one 16-example full FIT, each 64 Adam updates, total 576 gradient steps, CPU only, single-thread. No extra model library, payload, GitHub runner, paid API or fork. Capture elapsed model update time, fold results, source provenance, train sample counts, context coverage, original negative, sampled native sensitivity and regression guards. Fail on oracle fields, parent/source drift, FIT/DEV contamination, training on DEV, native repo mutation or false scientific promotion.

**Decision criteria:** identify whether public input aliases real different FIT outcomes, whether unseen DEV context/action coverage exists, whether native NCA responds to each public bit, and whether episode-held-out native predictions outscore equally informed strong conventional controls. Without measured superiority and true native action/value training, **reject promotion**, retain negatives and report only development readiness gaps. This does not automatically schedule FORGE research or fix Ygg's existing LU1 identifiability issues.

`AC17_ORIGINAL_SOURCE_EPISODES_NEW=0`  
`AC17_NATIVE_SOURCE_EDITED=FALSE`  
`AC17_INDEPENDENT_SCIENTIFIC_FIRST_USE=FALSE`  
`AC17_DEV_TRAINING_STEPS=0`  
`AC17_FIT_FOLDS=8`  
`AC17_CONTROLLER_OR_OWNER_POLICY_CHANGED=FALSE`
