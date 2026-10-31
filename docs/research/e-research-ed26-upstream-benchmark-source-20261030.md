# E Research E-D26 — externally sourced causal-benchmark selection (2026-10-30)

**Result:** Upstream source identity and interface review PASS; original benchmark installation, executable smoke test, baseline qualification, held-out first-use and native-model impact UNVERIFIED. This is a verification gate, not a scientific result, and no new model experiment was run.

## Read-only source verification

GitHub connector returned a specific upstream commit and successfully fetched the corresponding README at the same immutable commit for each candidate:

1. **Farama-Foundation/Minigrid**: commit `7f5853792ea7f04f75614661006d87fcf949f26d`; https://github.com/Farama-Foundation/Minigrid/commit/7f5853792ea7f04f75614661006d87fcf949f26d . The upstream README describes a lightweight Gymnasium grid-world suite with doors, keys, object interactions and BabyAI tasks. These make it suitable for observation-action-consequence and unfamiliar combinations if official mechanics, seeds and wrappers are pinned.
2. **CausalAILab/Causal-Gymnasium**: commit `c94e9a4cd3641588b6b8507e71ccee5c27032bdf`; https://github.com/CausalAILab/Causal-Gymnasium/commit/c94e9a4cd3641588b6b8507e71ccee5c27032bdf . Upstream README advertises Gymnasium-compatible `SCM` / `PCH` abstractions for observations, interventions and counterfactuals. Its documented environment families include Minigrid and tabular tasks. An agent must NOT get privileged causal graph or counterfactual answers as input; those may be used only in blinded evaluation.

This check verifies existence and upstream source description at SHA, **not executable compatibility or numerical correctness**. Note: upstream Minigrid README specifies Python 3.11+ and official Linux/macOS support, while the user's retail Windows deployment is a separate unsupported-until-proven qualification path. The local isolated Python environment was probed; `minigrid`, `gymnasium` and `causal_gym` are **not installed**. Therefore no claims of operational benchmark readiness or PASS tests.

## Selection

**Primary benchmark candidate:** official MiniGrid DoorKey and independent held-out key/door/object relation combinations, subject to version-pinned environment IDs, no oracle, and conventional controls. Use a single common public observation/action/consequence adapter so Wingless and Yggdrasil remain wholly independent native non-transformer learners; do not port or replace their architectures with a Q-table or transformer.

**Secondary causal falsification:** CausalGym source-pinned intervention environment with causal graph and counterfactual queries **evaluation-only**. Prefer a small CPU-capable task with no external binary assets.

## Required pre-execution qualifications, in order

- **Source birth:** record authenticated upstream commit, exact selected files/tree, license, dependencies, environment IDs and wrappers before first use. Verify transitive package versions; freeze FIT/VAL/HOLDOUT separate by environment-family generation, not merely random seeds.
- **Engineering smoke:** import reset/step, deterministic repeat under fixed seed, visibility/action legal masks, reward/resource parity and source-level contamination/oracle-negative checks.
- **Positive controls:** a conventional trained recurrent/state-space or memory-capable reinforcement learner, model-based learner, no-memory ablation, random, fixed handcrafted reference, and independent solver *evaluator-only*. Ensure equal training interactions, available public information, compute/memory accounting and actual test resource budgets.
- **Native mechanism:** separate Wingless causal/experience retention from Yggdrasil local-cell plasticity, with honest first-use provenance. This proposal is not implementation or authorization for model integration.
- **Promotion:** run required final regression and owner-authorized scientific acceptance separately, with original source and immutable receipt custody. FORGE autonomy must remain undisturbed.

**Decisions:** E-D21–25 thermal configuration closed as unsupported; E-D26 source selection PASS; benchmark execution **NOT STARTED**; first-use **UNVERIFIED**. No work was queued or controller touched.

**Next E-D27:** perform a source-pinned, dependency-bounded MiniGrid official DoorKey reset/step deterministic smoke on an authorized qualified runner; verify license and environment interface before training. If runtime remains unavailable, file a concrete blocker rather than replace the official source with a synthetic copy.

**Plain English:** We have verified where the real benchmark code comes from. We have not run it yet, so the next step is to prove the official environments work correctly before spending compute on model training.
