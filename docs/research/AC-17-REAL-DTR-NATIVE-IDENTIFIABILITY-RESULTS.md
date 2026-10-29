# AC-17 — Authenticated DTR public identifiability and native-locality diagnosis: qualified findings

**Conclusion:** SOURCE-BOUND DIAGNOSTIC ENGINEERING PASS ON WINDOWS + LINUX; NATIVE NCA PREDICTIVE ADVANTAGE NO-GO; INDEPENDENT SCIENTIFIC ADMISSION NO-GO. The native model demonstrably reacts to the public input, but available authentic observations are sparse and alias contradictory binary outcomes; eight episode-heldout folds produce a worse probabilistic forecast than strong FIT-trained conventional controls. This is a mechanism/representation *diagnosis*, **not** proof of hidden source confounding, action-local feature collisions in this exact NCA, or native causal learning.

## Immutable source identity and qualified code

- Existing [FORGE draft PR #1062](https://github.com/spoonman136668-ai/FORGE/pull/1062), stacked on unmerged AC-06 #1061. **Exact tested executable head `e4734749f65f8121d483c97090dc69187c4690ac`**, [GitHub Actions run #40794538606](https://github.com/spoonman136668-ai/FORGE/actions/runs/40794538606), completed **SUCCESS** both Linux and Windows. The push workflow is intentionally skipped to avoid duplicate expensive upstream installations; the PR workflow provides full source-bound checks.
- Authenticated original CausalAILab/Causal-Gymnasium DTR commit `c94e9a4cd3641588b6b8507e71ccee5c27032bdf`, original tree `fd8d8a67c1fc7fa62274dc7e12fb1e77945632f0`, original committed DTR bytes SHA-256 `e31eff82f862355057653d150967bb44a5ed57a6acaad57f7ecf2a551f6c6811`.
- Actual Yggdrasil *current active native research* commit `92c421a5475a27015a390efb88c373eb5f15379d` on `research/autonomy-yggdrasil-active`; unmodified `src/yggdrasil/nca.py` Git blob `7b15017b7f5c6f9b507bcf43f4545a3c972f40d1`, original `training.py` blob `af610c4334d2dd16415b39dd344ae2ed82ddd931`. Native class = `NeuralCellularAutomaton` shared-local spatial updater. External source-public BCE loss is **not** its original morphology training objective.
- AC-15 exact same 8 original-source public FIT episodes (seeds `760000..760007`, 16 public outcomes) and separate 4 DEV episodes (seeds `760200..760203`, 8 public outcomes) reused from fully qualified parent report. AC-17 executed **zero new DTR episodes**, performed no source counterfactual `ctf_do`, no sealed family or scientific first-use and no DEV optimizer updates. Existing AC-16 negative and original checkpoint evidence retained. No Wingless, Yggdrasil, FORGE main, F139 queue/controller/policy or steering-manifest mutation.

## A. Actual source-public identifiability evidence

The learner's exposed input was the binary tuple `(stage, observed_bit, scripted_action)`; stage 0 targets the *next observed bit*, stage 1 the terminal *public reward*. The authenticated 16 FIT events contained:

| Public tuple (stage, bit, action) | 0 outcomes | 1 outcomes |
| --- | ---: | ---: |
| (0,0,0) | 1 | 2 |
| (0,1,0) | 0 | 1 |
| (0,1,1) | 1 | 3 |
| (1,0,1) | 1 | 1 |
| (1,1,0) | 2 | 2 |
| (1,1,1) | 2 | 0 |

Exactly **6/8** possible public tuples appeared in FIT. **4/6** observed tuples have both binary outcomes, demonstrating explicit finite-sample *public-input outcome aliasing*: identical public tuples sometimes generated different consequences. A deterministic exact public lookup makes at least **5/16 errors on these FIT samples** (31.25% empirical minority-count error). The weighted empirical conditional entropy is **0.75 bits**. This is a property of the *observed samples and chosen projection*, not a universal bound on causal predictability. Additional public information, stochastic hidden exogenous variation or temporal memory could potentially matter; none is established as the correct cause here.

In the eight AC-16 frozen DEV public events, **2** combinations were never seen during FIT: `(stage=1,bit=0,action=0)` and `(stage=0,bit=0,action=1)`. Exact context/action generalization and calibrated uncertainty therefore remain essential. The small dataset cannot identify latent source confounders or claim unfamiliar-family transfer.

## B. Eight fixed leave-one-episode-out FIT folds

This evaluation holds out an entire genuine FIT *episode* (two public events) on each of eight folds, trains an unmodified original NCA for the same **64 fixed Adam updates per fold** from the other 7 FIT episodes (14 examples), and scores only the excluded two public outcomes. Conventional Laplace-smoothed contextual tabular and pooled FIT-prior predictions receive the **same 14 FIT events per fold**. No folds used DEV to train or choose hyperparameters.

| Out-of-episode predictor | Linux correct of 16 | Linux Brier ↓ | Windows correct of 16 | Windows Brier ↓ |
| --- | ---: | ---: | ---: | ---: |
| Native Ygg NCA (external BCE adapter) | **6** | **0.430051** | **6** | **0.430832** |
| Matched contextual tabular control | **8** | **0.311476** | **8** | **0.311476** |
| Matched pooled outcome prior | **9** | **0.270020** | **9** | **0.270020** |

Eight folds each trained **14 samples** and scored **2**, with **512 native Adam updates total**; a separate one-time full 16-event FIT replay was used solely for model feature sensitivity, not hyperparameter selection. The most challenging held-out FIT episodes were `760006` and `760007`: Linux native fold Brier `0.9987` and `0.9988`, with conventional tabular `0.5035` and `0.5422`. These are *diagnostics of brittle generalization*; do not state statistical significance or superior sample efficiency for the conventional methods on other families.

## C. Original local NCA responds to each public feature

Using the unchanged native source, the full-FIT model was trained and then frozen. AC-17 changed **only the externally encoded model-input bit** at public stage/observation/action one at a time for the same eight DEV contexts; no original source action or `ctf_do` was called. The trained model state SHA was identical before/after the sensitivity tests.

| Public input bit flipped | Mean absolute prediction change, Linux | Windows | Examples with negligible change |
| --- | ---: | ---: | ---: |
| Stage | 0.434343 | 0.434342 | 0/8 |
| Observation | 0.267303 | 0.267305 | 0/8 |
| Action | 0.283069 | 0.283065 | 0/8 |

The original shared-local network's predictions depend on all three encoded inputs, so a blanket “ignores the action” explanation is refuted for these test contexts. **This does not prove correct semantic identity, stable local role bindings, causal action influence, independent cell-local plasticity or persistent world memory.** The original morphology `training.py` is unchanged. Existing [FORGE #1031](https://github.com/spoonman136668-ai/FORGE/issues/1031) reports six initial-parameter feature collisions and failed reward-credit in a different *eight-cell native-development prototype*, and is an independent negative; do **not** transfer that result to the tested `NeuralCellularAutomaton` without a matched experiment.

## D. Exact Linux/Windows evidence

| Platform | GitHub artifact ID | ZIP SHA-256 | AC-17 JSON SHA-256 |
| --- | --- | --- | --- |
| Linux | `12863392446` | `34feadc3d9eabe191fdcb26f911226b5b82c1af1beed6aee52cd9aedfb79d5cf` | `0856802642f17f9c9ed64bc9e50533105e1e919f3ab3cbdbcd3dbf975057a23d` |
| Windows | `12863701625` | `dfbed3e59d3042ee5c7494196791f8009cb7200561888d17ee22f1c509a9de9f` | `72511a7fbc4d5b4d25e83db2c483b80771fd80b14efc992ad594729e8311ee46` |

Both archives contain complete prior AC-05–16 qualification records plus `ac17-report.json`. Public source data/counts, held-out assignment by FIT seed, exact conventional-control values and **6/16 native correct** match between platforms. CPU floating point and native model state hashes differ slightly across operating systems (not cross-OS byte identity). Current source constraints, data-allowlist, zero-new-episode, no DEV training, model-not-mutated-during-sensitivity and all no-science guards passed on both OSes.

## E. Decision for native research and FORGE

**AC-17 engineering PASS:** actual source-owned public evidence is insufficient for deterministic lookup and a current local NCA fitted to it remains substantially worse out of episode than controls. The model clearly responds to each public input; a purely input-insensitivity explanation is not supported. **The precise cause of the performance failure is not fully identified**: sparse samples, outcome stochasticity/aliasing, unsuitable external spatial feature projection, learning objective mismatch, or limited compositional transfer could contribute.

**AC-17 scientific NO-GO:** Do not select or deploy the external supervised adapter as a success, do not infer gains in native local distributed memory or self-improvement, do not pretend the old eight-cell collision is verified in this model, and do not autonomously edit controller/queue/steering. No new hidden/unknown-family episodes were touched.

**Next smallest useful gate, AC-18:** Use the existing authorized Ygg **local identifiability** lane [FORGE issue #1031](https://github.com/spoonman136668-ai/FORGE/issues/1031) rather than creating another generalized model. Source-pin the actual existing eight-cell local updater and its state-recovery/checkpoint, assess trained action-local collision persistence under a matched small public history with equal-information acting EMA/tabular controls, and include return-to-context retention and source-owned on-policy action consequences only where independently authorized. Preserve failures and environmental stochasticity. FORGE may choose/consume such advisory evidence **only at an eligible owner-controlled decision boundary**, never by this draft PR alone. Scientific original/unknown-family first-use remains separately NO-GO.

`AC17_CROSS_OS_SOURCE_BOUND_DIAGNOSTIC=PASS`  
`AC17_IDENTICAL_VISIBLE_INPUT_MIXED_LABELS=4_OF_6_OBSERVED`  
`AC17_UNSEEN_DEV_CONTEXT_ACTIONS=2_OF_8`  
`AC17_EIGHT_FOLD_NATIVE_BRIER_WORSE_THAN_MATCHED_CONTROLS=TRUE`  
`AC17_NATIVE_ACTION_FEATURE_INPUT_SENSITIVITY_NONZERO=TRUE`  
`AC17_CAUSAL_EFFECT_OR_NATIVE_INDEPENDENT_CELL_MEMORY_PROVED=FALSE`  
`AC17_NEW_DTR_EPISODES=ZERO`  
`AC17_SCIENTIFIC_FIRST_USE=FALSE`  
`AC17_FORGE_CONTROLLER_OR_NATIVE_REPOS_CHANGED=FALSE`
