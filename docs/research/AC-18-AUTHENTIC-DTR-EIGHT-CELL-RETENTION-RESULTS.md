# AC-18 — Historical eight-cell ring on authentic DTR public reward: qualified cross-OS results

**Engineering status: PASS Linux + Windows. Native predictive superiority: NO. Direct full-native bridge admission: BLOCKED by authentic source type mismatch. Original scientific first-use: NO-GO.**

## Source ownership and exact qualification

- [FORGE draft PR #1062](https://github.com/spoonman136668-ai/FORGE/pull/1062) remains **open/draft/unmerged**. Exact successfully tested executable workflow commit **`2852efa1997e8de5d734de6b763c003e2d0fe25c`**, [GitHub Actions run #40797373953](https://github.com/spoonman136668-ai/FORGE/actions/runs/40797373953): **ubuntu-latest SUCCESS, windows-latest SUCCESS**. An earlier initial AC-18 run failed **on Windows only** at test module import because the historical checkout's path was exported with a Unix-only `PYTHONPATH` separator; exact final code fixed that runner-context issue by running original Ygg tests from their own Git checkout. This is an engineering qualification repair, **not** an experiment result change.
- Real original source-owned FIT/DEV data: authenticated unmodified upstream `CausalAILab/Causal-Gymnasium` commit `c94e9a4cd3641588b6b8507e71ccee5c27032bdf`, AC-15 source `760000..760007` FIT (8 genuine episodes) and `760200..760203` DEV (4 genuine episodes). All 12 were **reused** from the already authenticated AC-15 public source report in the same CI job; AC-18 executed **0 additional original-source episodes**. No sealed/unknown-family source interactions or scientific first-use.
- The **actual original eight-cell `NativeRingMemoryDev`** came from historical Yggdrasil Git commit `a39171a76d0d7817e3563682bb139a9d7ecf37c4`, unchanged `yggdrasil/itd02_local_ring_memory_dev.py` blob `1db0835d5c99456bcf99a013d4836f49314a9d39` and original `itd02_native_task_bridge_dev.py` blob `b311ea7ea00c15d23e7bd43ff97bd10ce3d8b87c`. This historical package is **absent** from current Ygg active research branch `92c421a5475a27015a390efb88c373eb5f15379d`; do **not** claim current-production or active distributed-cell integration.
- Original Ygg source tests `tests/test_itd02_local_ring_memory_dev.py` were executed in the original checkout on both platforms. Original ring code and entire Yggdrasil source tree remain unchanged. New FORGE-only adapter `research/ac07_sourcefree/ac18_original_ring_dtr.py`, safety tests `test_ac18_original_ring_dtr.py`, prereg `docs/research/AC-18-ORIGINAL-EIGHT-CELL-DTR-RETENTION-PREREGISTRATION.md`.

## Native interface mismatch — hard NO-GO, not hidden relabeling

Original `NativeTaskRingBridgeDev.public_outcome(next_observation,reward)` restricts its public outcome label set to terminal classes `(-3, 0, 10)` and expects a legal successor observation string. Actual original DTR produces terminal **reward 1** and terminal successor **`None`**. AC-18 invoked both original methods and verified both invalid source values are rejected with `ValueError`. **Neither reward 1 → 10 nor None → a made-up next observation was performed.** AC-18 therefore operated directly on original eight-cell `NativeRingMemoryDev` using its legal public observation/reward interface as a *separate development projection*, not the full `LocalTaskRuntime` / `NativeTaskRingBridgeDev` and not as an online DTR action policy.

The frozen external mapping was stage-0 public binary observation to `LRV,MRV`, stage-1 public binary observation to `docked_MRV,docked_LRV`, source action 0 → `TurnAround`, source action 1 → `GoForward`. Ring's third action `Backup` has no corresponding legal DTR action and was **never sent** to the source. Ring predicted a pre-feedback raw Q score for the *actual scripted public action*, then learned from source-owned immediate reward 0 at stage 0, terminal reward 0 or 1 at stage 1. This did not infer stage-0 causal credit from the later terminal. Original `choose` was only inspected for disallowed-action risk. Score clipping to 0–1 is an explicitly labeled, uncalibrated squared-error proxy, **not a calibrated probability or on-policy reward return**.

## Verified actual FIT and cold DEV outcomes

The original ring received exactly **16 public reward updates** (two per FIT original-source episode). Its original learnable parameter digest changed and **four of eight local retention gates** changed from initialized logit 1.0: cell 1 `+0.00868558`, cell 3 `+0.01001650`, cell 4 `+0.00073090`, and cell 7 `+0.01240423`; all others unchanged. This confirms public reward credit reached existing local gates; it does not establish globally useful locality or compositional transfer.

A **604-byte** SHA-256-enveloped original ring checkpoint passed byte-identical cold restoration and public DEV replay. Its exact original learned checkpoint SHA-256 was **`e68d1524533b703f3eabb61741ea7093317c7e4630c87cd7fba2d1086397a4f4`**, learned parameter digest **`b62cafd8f81ebca8e3eb4077ff0075e89cbeae856b99c48a2141deb0b3369615`**. Both hashes are **identical Linux and Windows**. DEV fitting updates: **zero**, and original parameter identity was unchanged during DEV.

| Model / fitted control | Linux correct / 4 DEV terminal rewards | Windows correct / 4 | Brier squared-error proxy ↓, both OS |
| --- | ---: | ---: | ---: |
| Historical original 8-cell ring, raw Q clipped to 0–1 | **2/4** | **2/4** | **0.395318** |
| Fitted acting EMA, alpha=.5 | 2/4 | 2/4 | **0.232666** |
| Fully FIT-trained contextual tabular | 2/4 | 2/4 | **0.246094** |
| FIT-pooled prior | 2/4 | 2/4 | **0.265625** |

**Native ring loses to every conventional fitted control on this tiny DEV sample by squared-error/Brier proxy.** Baseline supervision was terminal-only (8 FIT reward labels), whereas ring also processed eight stage-0 public immediate-zero rewards (16 updates); comparisons are equal access to relevant public source information but not identical model or compute budgets. Any categorical native superiority claim is **false**.

Three of the four DEV `(stage-0 bit, stage-1 bit, scripted terminal action)` tuples had **no exact FIT support**. Native original action-head raw Q scores fell outside 0–1 on **two of eight DEV stage records** and were clipped for the proxy. The native's unsupported third action was selected **zero of eight** DEV stage decisions, but DTR action-admission remains NO-GO because the full bridge reward/successor types are incompatible regardless of these observed choices.

## Action-local memory, retained context, and collisions

- Frozen source FIT replay created **eight distinct stage/action local-feature groups**, and **zero groups with different source rewards sharing identical frozen action-local feature tuples**. This is not proof of identifiability: it is a small fixed-sample absence of a particular group collision under the original eight-cell routing. The independently reported six initial-parameter action-local collisions from [FORGE issue #1031](https://github.com/spoonman136668-ai/FORGE/issues/1031) concerned a **different setup**; neither negated nor resolved here.
- Original source-backed **A–B–A** replay: seed `760000` source-public A context `(0,1,0)` produces frozen terminal ring Q **0.22663239948307104**; intervening public B seed `760001` context `(1,1,0)` produces Q **0.11047428900887474**; returning to A at `760004` with identical public A context reproduces original Q **0.22663239948307104**. This is an **unchanged frozen-weight checkpoint + per-episode reset replay**, not learning B and retaining A after intermediate training.
- Exactly **2,048** local directed neighbor message accounting units were recorded across FIT, DEV, and frozen replay (not a bitwise network-bandwidth measurement). Original ring uses two bounded hops, local action-head signals, no full observation array exposed to its readout. No learned independent cell-specialization, native return utility, unfamiliar-family transfer or damage recovery was verified.
- CPU/perf memory measurements are present per OS in the archived source data but **not directly comparable to the tabular baseline without matched benchmark harness**.

## Exact evidence artifacts

[Final exact cross-platform run #40797373953](https://github.com/spoonman136668-ai/FORGE/actions/runs/40797373953), tested commit `2852efa1997e8de5d734de6b763c003e2d0fe25c`.

| OS | Artifact ID | ZIP SHA-256 | `ac18-report.json` SHA-256 |
| --- | --- | --- | --- |
| Linux | `12865360117` | `dde56e90355c2ff09c78a3790056b6a04c1e205aa5c6a7957386e73cc31c14b7` | `de74656aa8cbef76f995a22d1253804583ac18c03f9715efa740ca86cd08ef10` |
| Windows | `12864561884` | `3607a01e134cff549422e04dcd0a33e7aef449e8e9e9d4a376cc76c59e43d738` | `2cea6c95247e36daf2a944f965b39184031da2897259d211f556655864fd95a8` |

I independently compared both archived reports: **identical** trained parameter/checkpoint digests, source FIT/DEV seed IDs, 16 updates, retention gate deltas, all DEV reward predictions and baseline metrics, action-local collision counts and A–B–A replay records. Whole report and ZIP SHA-256 differ due runtime resource timing and other platform-dependent archived evidence.

## Disposition and next eligible gate

**AC-18 ENGINEERING PASS:** existing historical eight-cell ring can learn from genuine independently sourced public DTR rewards, alter local retention gates, serialize/recover a tiny persistent checkpoint and reproduce fitted frozen predictions across Linux/Windows. This is a more local original Ygg mechanism than AC-16's external supervised NCA adapter, but **its DEV performance remains worse than EMA/tabular**.

**AC-18 SCIENTIFIC NO-GO:** direct full native bridge rejects real DTR source categories and no current active-branch production integration exists. Do not silently normalize source reward1 to 10, fill None with a fake observation, or interpret frozen A–B–A replay as trained retention after intervening learning. No on-policy decision utility, confident causal credit, unfamiliar-family transfer or independent source-birth/first-use witness. Nothing was promoted to FORGE's owner steering manifest, selected by controller, merged to main, or written into active Ygg/Wingless repos.

**Next gate AC-19 (conditional, narrow):** Qualify an *actual source-native typed adapter* that represents binary DTR rewards and terminal successor None without loss of source identity, while preserving original eight-cell locality and original `LocalTaskRuntime` authorization boundaries. This must first reconcile native active-branch and historical code ownership; no autonomous rollout without qualified owner-controlled authority. Compare source-native action outcomes to fitted EMA/tabular under matched legitimate source actions and cost, and reject gains unsupported by realized held-out on-policy reward. Under no circumstances authorize protected unfamiliar-family first-use implicitly.

`AC18_REAL_DTR_PUBLIC_RING_FIT_COLD_RESTORE=PASS_BOTH_OS`  
`AC18_REAL_SOURCE_EPISODES_NEW=ZERO`  
`AC18_CHECKPOINT_CROSS_OS_BYTE_IDENTITY=PASS`  
`AC18_LEARNED_LOCAL_RETENTION_GATES_CHANGED=TRUE`  
`AC18_PREDICTIVE_SUPERIORITY_OVER_EMA_OR_TABULAR=FALSE`  
`AC18_FULL_NATIVE_BRIDGE=NO_GO_TYPE_MISMATCH`  
`AC18_ACTIVE_BRANCH_PRODUCTION_INTEGRATION=FALSE`  
`AC18_PROTECTED_SCIENTIFIC_FIRST_USE=FALSE`
