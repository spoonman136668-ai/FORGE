# ITD-02: four-stage native-intelligence environment expansion (research-only design contract)

Status: **PROSPECTIVE DESIGN / NO SOURCE RUN / NO SCIENCE / NO MODEL PROMOTION**  
Owner direction: expand the existing common source-selected research interface in this exact order: compositional MiniGrid -> causal interventions -> persistent-memory challenge -> independent transfer.  
Design ancestor: FORGE MG16 prospective source-only branch `ce70ee2d98cd9bc8862bedb8ed909569112d2be4` (PR #1118). This file is additive and must not edit existing MG15/MG16 frozen evidence or candidate sources.

## 0. Preserve the actual research frontier

- Authentic MG15 original-world run [FORGE #1116](https://github.com/spoonman136668-ai/FORGE/pull/1116), run [40847663087](https://github.com/spoonman136668-ai/FORGE/actions/runs/40847663087), exact original trace SHA256 `03b22d2a8a1b87928cb9e5b72ff912fa1e99c914166524bd8a04e9642dbd0f96`: Wingless DK14, Yggdrasil R18, and mission-conditioned conventional actors each scored **0/3 DoorKey, 3/3 goal-only**, repeatedly choosing original action 2 for 576 DoorKey steps; mission-blind conventional scored 1/3 DoorKey. This is negative evidence, not learned composition.
- MG16 state-exact reward gating is separately source-qualified but **has not yet undergone an original Farama world trial**. Native candidate identity remains Wingless [DK16 #432](https://github.com/spoonman136668-ai/Wingless/pull/432) `e2ff8bcd4b9e84f4284e07a44034777238abcc9e` and Yggdrasil [R20 #690](https://github.com/spoonman136668-ai/Yggdrasil/pull/690) `a9942978f92e762e404fe50ce29445ea4639b4c2`. The separately frozen MG16 DoorKey/Empty cohorts and the blocked consequence-vs-episode factorial [#1117](https://github.com/spoonman136668-ai/FORGE/pull/1117) remain independent.
- No new cohort may reuse a consumed MG11-MG16 development source event/seed or claim an original holdout based on it. Legacy results remain immutable. Never retrospectively alter hypotheses, thresholds or cohort eligibility.
- This document is an **architecture/experiment-design contract**, not a final registered scientific trial: each stage requires a subsequent distinct, exact-source preregistration with pinned upstream commit/tree, FIT/DEV/sealed test origin, seeds and action budgets, comparison algorithms/capacity, success/failure thresholds, before any new executable or model development. Each stage must separately prove its source qualification and first-use custody.

## 1. Common public source-selected interaction contract

Reuse the existing MG15/MG16 source interaction and custody model as the foundation, not a parallel controller:

1. The independently authored original environment owns `reset`, `step`, observation, source reward, termination/truncation and legal action set. An **isolated adapter** supplies a strictly versioned public observation envelope, `episode_id`, source identity, legal action set, public mission when supplied by source, and a single selected `action`. Each actor receives the actual selected source consequence `next_public, reward, terminated, truncated`, exactly once. No collector-selected rescue actions, planner stages, goal coordinates, hidden map, private environment state, oracle outcomes or invented counterfactuals are allowed.
2. Preserve native architecture independence: Wingless remains native Go; Yggdrasil remains a local-cell implementation. The adapter changes public wire format only where necessary; original native policy/parent source SHA and checkpoint lineage remain independently frozen. **Do not falsely claim identical observation modalities across environments**. Each new environment requires a separately reviewed public encoding; prohibit lossy hand-crafted stage answers.
3. Compare agents on identical upstream source, information privileges, FIT data exposure, own-selected action and intervention counts, reset cohorts, budgets and evaluation windows. Report discrepancies in parameters/compute/representation explicitly. Include independent conventional model-based, recurrent, Bayesian (where applicable), frozen-memory and random ablations; no native superiority claim without sufficiently matched controls.
4. Source receipt per event: original upstream commit/blob and environment ID; exact source reset seed/cohort; full public observation and mission digest, action ID, returned public consequence, reward/termination, selected-action sequence index, deterministic trace/checkpoint hash. Require independent repeat execution on two hosts when supported; retain source/platform nondeterminism as a blocker instead of omitting difficult worlds. Separate clock/CPU/RSS/energy accounting from source trace digest.
5. Evaluation must preserve FIT vs development vs genuinely sealed first-use segregation, publicly freeze outcome criteria beforehand, control for accidental overlap/contamination, and capture paired per-world metrics and uncertainty. Publish all negative trials. A GitHub CI pass is **engineering qualification**, never scientific acceptance.
6. No changes to FORGE original F139 owner/controller, queue, scientific authority, accepted models, protected main, KTRADE, CKB-plane, broker or Atlas/G29 required checks. No new scheduler or queue consumer. All stage experiments are independently opt-in and must be authorized through existing execution/qualification authority; this document dispatches nothing.

## Gate 1 — Extend native MiniGrid compositions first

**Question:** Do authentic, selected-public action/consequence experiences support recombination of unfamiliar key / door / object dependencies and delayed effects, rather than memorizing a mission-global action?

- Original benchmark family: the already source-pinned Farama MiniGrid commit `7f5853792ea7f04f75614661006d87fcf949f26d`. Candidate original environment families to inspect and pin individually: `MiniGrid-DoorKey-6x6-v0`, `MiniGrid-UnlockPickup-v0`, `MiniGrid-BlockedUnlockPickup-v0` and a source-registered KeyCorridor or ObstructedMaze configuration where available. Confirm every environment ID and upstream source implementation before preregistration; do not create a custom puzzle and mislabel it as original upstream.
- Construct **training** on disjoint simple relationships and **unseen combination cohorts** with withheld object identity/color, dependency order, location/layout and longer action-to-reward lags. Use only authentic source instances and actual terminal reward; no manually relabeled intermediate rewards, human-selected door-opening prefix or special goal features.
- Treat `key pickup -> door unlock -> object/goal` as evaluator-only event sequence, not exposed policy hints. Measure true goal completion, dependency-order errors, unique selected causal consequences, source action diversity, lag-to-goal, loop fraction and cold-checkpoint retained improvement. Report paired intervention ablation of source consequence learning ON/OFF and episode-history ON/OFF once [MG16 factorial #1117](https://github.com/spoonman136668-ai/FORGE/pull/1117) has a verified isolated API; otherwise mark that factorial **BLOCKED**, not negative.
- Same parent policies, MG16 exact-context candidate, equally informed source-public model-based or contextual conventional, equal-FIT mission-blind and frozen variants; no difference in public mission availability concealed. First demonstrate source-family public adapter reproducibility and native action-reward parity; only then run new, separately registered development and sealed cohorts.

**Gate 1 GO:** New intact source/adapter/custody PASS and a separately preregistered genuine unseen-composition comparison; positive learning/generalization only if goal and dependency metrics surpass frozen matched controls under precommitted thresholds with source-authentic delayed outcomes. Do not use reward-only synthetic tests as world evidence.

## Gate 2 — CausalGym interventions, not privileged causal graphs

**Source identity to admit:** [CausalAILab/Causal-Gymnasium](https://github.com/CausalAILab/Causal-Gymnasium), the Gymnasium/SCM/Pearl-hierarchy source with `see`, `do`, and `ctf_do`. This is **not** the unrelated language-model causal-interpretability benchmark also named CausalGym.

- Isolate one small original causal environment first. Preserve original SCM/graph for **evaluator-only ground truth**. Actors must not read `get_graph`, structural equations, latent confounders, seed-based intervention answers, or source-private state.
- Declare distinct access regimes: passive observation; active environment intervention; optional evaluator-only counterfactual assessment. Counterfactual or oracle access must be equal for all arms if explicitly permitted; it is not assumed to be a normal interaction. Never leak an oracle-generated `ctf_do` answer as if source actually returned it after chosen `step`.
- Compare Wingless and Yggdrasil independent learners with Bayesian causal-discovery and model-based intervention-planning baselines given exactly the same public observations/intervention opportunities, plus purely observational, random-intervention, and graph-agnostic controls.
- Record intervention cost, source causal-effect accuracy, predictive log loss or calibration, unseen intervention outcomes, intervention efficiency/regret and graph precision/recall only where identifiable. Counterfactually indistinguishable graphs must not be scored as falsely distinguishable. Use disjoint unknown-structure variants and preregister graph-equivalence handling.

**Gate 2 GO:** Original SCM and independent replays authenticated, equal-information interventions demonstrable, and a new source-pinned precommitted intervention generalization outcome. No causal-discovery or architectural superiority claim from action reward alone.

## Gate 3 — Memory Gym retained cognition under distraction

**Source identity to admit:** [MarcoMeter/endless-memory-gym](https://github.com/MarcoMeter/endless-memory-gym), covering Mortar Mayhem, Mystery Path and Searing Spotlights; verify exact upstream commit and the environment's public action/observation semantics before any native integration.

- Begin with source-authentic finite variants; graduate to original endless variants using progressively longer histories with frozen length ladders. Do not shorten episodes post-result or truncate difficult failures.
- Measure decision accuracy vs cue-to-use delay, retained earlier events vs recently seen distractors, recovery after observational interference, within-episode memory durability, repeated read/write, checkpoint/cold-restore parity and bytes/cell state/CPU/RSS per successful retained dependency.
- Wingless memory and Yggdrasil local-cell storage are independently native. Compare memory-off, random/fixed buffer, capacity-matched episodic/recurrent GRU, and stronger standard recurrent/attention controls where reproducible; the comparator's use of transformer memory does **not** license a transformer foundation in either native model.
- Do not label all success as memory: test observation-only and finite-history ablations, cue shuffling, distractor reversal, and alternative success policies to falsify shortcut explanations. Prevent evaluator from inserting hidden reference cues into native observations.

**Gate 3 GO:** Reproducible original source, conserved selected events, delayed-memory improvement beyond matched memoryless/frozen controls on new precommitted histories, and explicit resource/retention cost. A CI pass without retained dependency performance is not a memory breakthrough.

## Gate 4 — Independently qualify transfer in MiniHack or Crafter

**Preferred first independent original source:** [facebookresearch/minihack](https://github.com/facebookresearch/minihack), initially a simple independently generated source task then progressively longer multi-object dependencies, preserving the original Gymnasium `reset/step` and authenticated source mission/action/observation. This is **not** automatic proof of transfer because it has a different action/observation schema from MiniGrid.

**Crafter hold:** [danijar/crafter](https://github.com/danijar/crafter) is a second option only after reproducibility qualification. Earlier authentic Yggdrasil [MR34B0 #390](https://github.com/spoonman136668-ai/Yggdrasil/pull/390), [MR34C #391](https://github.com/spoonman136668-ai/Yggdrasil/pull/391) found source-world **physical transition divergence** across cross-OS and same-OS repeated action streams with source `e04542a2159f1aad3d4c5ad52e8185717380ee3a`. Preserve `NO-GO`; don't cherry-pick seeds or weaken reproducibility. Resolve with a new transparent source/host/trace contract or use MiniHack.

- Freeze independent source, source-public normalization and native interface separately. Use trained **source-frozen** Wingless/Yggdrasil mechanisms from prior gates, then report **zero-shot**, fixed-budget adaptation and scratch-trained control as distinct tracks. Do not tune on held-out transfer tasks.
- Comparator set: equally exposed and resource-matched conventional world-model/recurrent, frozen own model, source-naive, random. Report task success, chain length, action efficiency, failed prerequisites, novelty/reuse, budget and retained learned-state quality. Document unavoidable observation or action asymmetries.
- Require separate source-qualified preregistration, two independent genuine-world executions where deterministic, independent scientific first-use controls and evidence custody. MiniGrid/CausalGym/Memory Gym positives are hypotheses only; **never** substitute prior gates' passing evidence for independent transfer qualification.

**Gate 4 GO:** Independently authenticated source and a separately eligible held-out cross-environment result that survives controls and information/resource matching. Otherwise preserve a clear negative or BLOCKED disposition.

## Release and speed guarantees

- Research-only branches and draft PRs until stage-specific acceptance; no merge/promotion/dispatch implied here.
- Reuse previously qualified exact unchanged source/tree/test foundations by content identity; verify all relevant provenance, toolchain, harness and interface keys. Run focused changed-interface tests, then **one mandatory final integration/full regression**, vetted build and existing scientific custody checks. Fall back to fresh qualification on drift.
- No new competing research loop. Dedicated original science authority stays separate from advisory planning, and FORGE autonomy must not be paused or replaced to attempt this portfolio.
- This document intentionally creates no runnable script, workflow dispatch, accepted model change, sealed-test query or automatic research schedule.

## Primary upstream references

- [MiniGrid DoorKey source semantics](https://minigrid.farama.org/environments/minigrid/DoorKeyEnv/)
- [MiniGrid Blocked Unlock Pickup](https://minigrid.farama.org/environments/minigrid/BlockedUnlockPickupEnv/)
- [CausalGym SCM/intervention source](https://github.com/CausalAILab/Causal-Gymnasium)
- [Memory Gym original source](https://github.com/MarcoMeter/endless-memory-gym)
- [MiniHack original source](https://github.com/facebookresearch/minihack)
- [Crafter original source](https://github.com/danijar/crafter)
