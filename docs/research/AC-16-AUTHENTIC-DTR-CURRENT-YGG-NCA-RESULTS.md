# AC-16 — Current Yggdrasil native local NCA on authentic DTR public data: cross-OS result

**AC-16 development qualification: PASS (both operating systems). Native predictive superiority: NOT ESTABLISHED, and negative against matched controls. Original scientific first-use and native action-policy admission: NO-GO.**

## Immutable code and evidence

- FORGE exact qualified source/test/workflow commit **`431ccb21ee3cd2bc989e1a52f8ec667a5432d2be`**, [Actions run #40793254797](https://github.com/spoonman136668-ai/FORGE/actions/runs/40793254797), both Linux and Windows **SUCCESS**, draft PR [#1062](https://github.com/spoonman136668-ai/FORGE/pull/1062). Original earlier qualification at `9f654174` correctly **FAILED** because the source-free regression discovered the torch-dependent test before the original source-bound PyTorch CPU environment had been installed. Repair `431ccb21` isolates NCA tests to that environment and preserves source-free tests. No source/science or authority changes.
- Real **current Yggdrasil active native research branch** `research/autonomy-yggdrasil-active`, Git SHA `92c421a5475a27015a390efb88c373eb5f15379d`; authentic unmodified original `src/yggdrasil/nca.py` Git blob `7b15017b7f5c6f9b507bcf43f4545a3c972f40d1`, and original morphology `training.py` blob `af610c4334d2dd16415b39dd344ae2ed82ddd931`. It uses 3×3-local spatial perception and a shared 1×1 local update, not an action/reward API.
- Data: AC-15 upstream `CausalAILab/Causal-Gymnasium` DTR at `c94e9a4cd3641588b6b8507e71ccee5c27032bdf`; previously authenticated **8 FIT / 4 DEV true original-source public episodes**. This gate reused the qualified AC-15 report in the same CI job. **No new upstream episodes**; only 16 real-source FIT public outcomes and 8 separate public DEV outcomes. Exact FIT/DEV source validation and parent source commitment checked.
- Code: `research/ac07_sourcefree/ac16_current_ygg_nca.py`, focused `test_ac16_current_ygg_nca.py`, preregistration `docs/research/AC-16-REAL-DTR-NATIVE-YGG-NCA-PREREGISTRATION.md`. The adapter (not a Ygg native training method) maps public stage, binary observation and scripted action into three nearby cells on a 5×5, 8-channel alpha-alive grid. It reads one central output channel after two original NCA steps with shared-local weights and fixed `fire_rate=1`; externally trains binary outcome cross-entropy, not Yggdrasil morphology/regeneration. It does not change the NCA architecture or source tree.
- Exactly **528** unmodified NCA trainable parameters, FIT-only **64 Adam updates** (fixed seed 20261028, LR=.02), CPU PyTorch 2.3.1+cpu, frozen DEV and checkpoint restore. An identical-information FIT-trained contextual tabular predictor and global FIT outcome prior are independent controls; a fixed cyclic shift of FIT targets is a negative control. No DEV tuning, target leakage or original source privilege.

## Actual numbers: do not conflate FIT fit with DEV learning

| Result | Linux | Windows |
| --- | ---: | ---: |
| Genuine source-owned FIT examples | **16** | **16** |
| Genuine source-owned DEV examples | **8** | **8** |
| New DTR source episodes this gate | **0** | **0** |
| Original NCA param count | **528** | **528** |
| Initial FIT cross-entropy | 0.693147 | 0.693147 |
| Final FIT cross-entropy | 0.521425 | 0.521425 |
| Native NCA DEV accuracy | **3/8** | **3/8** |
| Native NCA DEV Brier (lower better) | **0.424755** | **0.424749** |
| Fully fitted contextual tabular DEV accuracy/Brier | **3/8 / 0.323819** | **3/8 / 0.323819** |
| Pooled fitted prior DEV accuracy/Brier | **5/8 / 0.239198** | **5/8 / 0.239198** |
| Rotated-FIT-label negative control DEV accuracy/Brier | **6/8 / 0.209142** | **6/8 / 0.209148** |
| Torch native checkpoint serialized | **3,924 bytes** | **3,924 bytes** |
| Cold-restored checkpoint predictions | **PASS** | **PASS** |
| DEV optimizer steps/updates | **0** | **0** |

Native trainable weights changed under FIT labels, train loss declined, a fresh native NCA restored those weights from the saved checkpoint, and frozen DEV predictions were reproducible within each OS. Linux and Windows *binary accuracy and experiment interpretation agree*. The exact floating values, trained state digests and torch checkpoint SHA **differ slightly across platforms**, which is expected with platform-dependent numerical kernels/serialization and is **not** byte-identical checkpoint parity. A successful per-OS cold restore does not imply cross-OS byte identity.

The native NCA **loses to both FIT-trained conventional probabilistic baselines by Brier score**, and a deliberately wrong FIT-label negative control also scores better on these eight DEV examples. The latter does not prove the negative model is better; it shows this small development split is incapable of supporting strong mechanism claims. No unknown-family transfer, independent local on-policy exploration, native causal credit assignment, action-policy returns, damage recovery or persistence across task families was measured. Never call the original morphology-training objective successful because an external supervised loss decreased.

## Artifact custody (exact tested commit)

| Platform | GitHub Actions artifact ID | ZIP SHA-256 | `ac16-report.json` SHA-256 |
| --- | --- | --- | --- |
| Windows | `12863290402` | `63ad542890aa8ca3f30ab824320f5508fdaf510a14a0b9319603d6a4509ad299` | `a7ba428db19052df684d661af49ae5e9c9f2ed7930dd734e931c148bb1761f47` |
| Linux | `12862801736` | `e0e669b3896bbdc63d93dbb05b88f817e491fba82519f93c6857f5d4756dfae2` | `574b799a66825439d51036e59c7fcb45d47f3c1084135878c05fb155b6831ff1` |

Archives include AC-05..15 source-bound findings and AC-16 results. The source-native tests preserve original Ygg commit/blob identity, original Causal-Gymnasium source and unprivileged event whitelist. Both GitHub-hosted jobs passed. Do not assert a production integration or next-owner approval.

## Gate decision and next work

**AC-16 PASS = a development-only bridge to Ygg's current native spatial local update, under an external prediction loss.** **AC-16 NO-GO = scientific/native transfer or superiority.** The learner's 3/8 performance and inferior Brier mean this adapter should not be promoted or spend scarce training budget as a purported advance. Prioritize a **representation/identifiability diagnosis** and source-public longer, predeclared development horizon only if existing native-lane owner approves, with fair fitted tabular/EMA controls. Do not replace the native morphology objective with a DTR-only reward trainer or create parallel research work. The Ygg action-local collision and negative-credit issues from FORGE #1031 remain unresolved; Wingless receives no new API or fabricated integration.

**AC-17 recommended:** reconcile this negative against active Wingless and Ygg native research/owners; attempt a more native **local-memory representation** only where preexisting owner-approved interface supports source-public consequences and memory, with matched controls and *realized on-policy* evaluation, and do not claim unfamiliar-family scientific progress until fully authenticated independent FORGE FSA/source-birth custody. Another set of eight retrospectively scored examples alone would not close the north-star gap.

`AC16_CROSS_OS_AUTHENTIC_PUBLIC_DEVELOPMENT=PASS`  
`AC16_UNMODIFIED_CURRENT_NCA_FIT_AND_COLD_RESTORE=PASS`  
`AC16_TABULAR_PREDICTION_SUPERIORITY=NO`  
`AC16_NATIVE_NCA_DEV_BRIER_GREATER_THAN_FITTED_CONTROLS=YES`  
`AC16_NO_NEW_ORIGINAL_SOURCE_EPISODES=TRUE`  
`AC16_REAL_NATIVE_ACTION_POLICY=NOT_TRAINED`  
`AC16_SCIENTIFIC_FIRST_USE_AND_ACCEPTANCE=FALSE`  
`AC16_NATIVE_REPO_F139_CONTROLLER_OR_QUEUE_CHANGED=FALSE`
