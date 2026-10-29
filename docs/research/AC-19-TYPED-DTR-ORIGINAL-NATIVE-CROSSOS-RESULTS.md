# AC-19 — Lossless original DTR to historical Ygg eight-cell runtime: qualified findings

**Status: ENGINEERING PASS on Linux and Windows; scientific/native superiority NOT ESTABLISHED; original historical full bridge and active native production integration remain NO-GO.**

## Source and qualification

- Existing stacked draft [FORGE PR #1062](https://github.com/spoonman136668-ai/FORGE/pull/1062); executable commit **`b557a82c3812f04b8bc4ffd26895a6e363a8a335`**; scoped accelerated [Actions run #40799621109](https://github.com/spoonman136668-ai/FORGE/actions/runs/40799621109) **SUCCESS both GitHub-hosted Linux and Windows**. The accelerated replay consumed only previously qualified original public-source receipts, so it did not reinstall PyTorch or execute any new original DTR episodes.
- Original Causal-Gymnasium DTR source commit `c94e9a4cd3641588b6b8507e71ccee5c27032bdf`. Source FIT/DEV immutable evidence came from independently cross-OS qualified [AC-18 run #40797373953](https://github.com/spoonman136668-ai/FORGE/actions/runs/40797373953), archived in the same original FORGE repo. **8 FIT episodes / 16 public action/consequence pairs and 4 DEV episodes / 8 public pairs**, source-owned and already collected. Before use, the new workflow validated:
  - Linux `ac15-report.json` SHA-256 `68508db981776033d403094f237c17dbbfbadf822ac9eca011feb05d50cba286`, `ac18-report.json` `de74656aa8cbef76f995a22d1253804583ac18c03f9715efa740ca86cd08ef10`.
  - Windows `ac15-report.json` SHA-256 `071512caf92b82d8b3ed619d79d7741447be72bde29ae9b1b64fd42de2e39077`, `ac18-report.json` `2cea6c95247e36daf2a944f965b39184031da2897259d211f556655864fd95a8`.
- Actual unchanged historical Yggdrasil development source at Git `a39171a76d0d7817e3563682bb139a9d7ecf37c4`; original `LocalTaskRuntime` from `yggdrasil/task_runtime.py` blob `68a1423e0bd7206af511212c14b6ce8534154cc2`; `NativeRingMemoryDev` from `yggdrasil/itd02_local_ring_memory_dev.py` blob `1db0835d5c99456bcf99a013d4836f49314a9d39`; full original source bridge blob `b311ea7ea00c15d23e7bd43ff97bd10ce3d8b87c`. The historical original ring is NOT the current Yggdrasil active research branch and no active native code was changed.
- Adapter `research/ac07_sourcefree/ac19_typed_original_native_bridge.py`, tests `test_ac19_typed_original_native_bridge.py`, fast provenance-qualified cross-OS workflow `.github/workflows/forge-ac19-source-replay-fast.yml`. The original historical ring's own source-free tests also passed as part of this run.

## Encoding correction — preserve audit history

The **initial AC-19 proposed input code** one-hot encoded stage×observation at sites 0–3 and action at sites 4–5. Inspecting the original `LocalTaskRuntime.features(bits,i=5)` established that the reward readout can see **only site 5 and adjacent sites 4 and 6**. The first layout was locally blind to stage/observation. Its previous short-lived CI attempts were cancelled and have **no admissible native predictive conclusion**.

Before the completed source-bound AC-19 run, we corrected `before` to exact three public bits at sites **4 = stage, 5 = current observation, 6 = scripted action**, reserved sites 0–3 and 7 zero. Every one of the **eight** legal binary input tuples is now distinct in the original reward cell's own one-hop feature neighborhood; regression tests verify this and reject the prior context-blind scheme. The output encoding remains injective for all **six** supported outcomes: next observation `0`/`1`/real terminal `None`, exact terminal flag and real reward `0`/`1`. The source's terminal `None` is represented by a separate typed sentinel/mask, **not a fake source observation**. Reward `1` remains `1`, **not recoded to the original bridge's disallowed reward 10**.

This is a structural repair discovered before **valid final scientific measurement**, not tuning an optimizer or learning rule to DEV. This report explicitly supersedes the earlier preregistration paragraph specifying one-hot 0–3 input sites; original commits remain in history for review.

## Actual original native learning and fair comparisons

Both original unmodified implementations trained on the exact same 16 source-owned public FIT pairs; the original `LocalCountControl` received the same eight-cell before/after pair at each step. Original `LocalTaskRuntime.observe` executed **16** native local training events, and `NativeRingMemoryDev.feedback` executed **16** reward updates. Both original genome/role parameters and original ring learned parameters changed. Original `LocalTaskRuntime.snapshot/restore` and `NativeRingMemoryDev.checkpoint/restore` passed cold restoration; all eight DEV predictions were frozen with **zero** additional updates. Neither model selected an action for the upstream environment; original FIT/DEV actions remain source-scripted and unchanged. Only terminal DEV reward 0/1 scored at original output site 5.

| Authentic source DEV terminal outcomes (4) | Linux correct / 4 | Windows correct / 4 | Brier score (lower better), both OS |
| --- | ---: | ---: | ---: |
| Original native `LocalTaskRuntime`, corrected external typed adapter | **2** | **2** | **0.23846717** |
| Original `LocalCountControl`, same eight input/output cells | **0** | **0** | **0.40625000** |
| Fitted source-history acting EMA | **2** | **2** | **0.23266602** |
| Fitted source-history contextual tabular | **2** | **2** | **0.24609375** |
| FIT-pooled terminal reward prior | **2** | **2** | **0.26562500** |

The native original does better than its matched original local-count control and two source-history conventional controls **in this tiny DEV set**, but loses to the fitted acting EMA by Brier **0.00580115**. Therefore **`native_beats_all_controls = false`**. This is a preliminary engineering comparison of a historical model under an external encoding, **not** proof of generalization improvement, causal learning, efficient native intelligence, independent local plasticity, or policy value. Four terminal examples do not establish statistical superiority. The original full native `NativeTaskRingBridgeDev` still rejects real source `reward=1` and `terminal successor=None` and is **not replaced in production** by this external adapter.

## Cross-platform evidence and numerical precision

| Platform | Exact run artifact ID | Artifact ZIP SHA-256 | `ac19-report.json` SHA-256 |
| --- | --- | --- | --- |
| Linux | `12865805234` | `c807870c77f2c1c334a67dd90bd4e99703ce324ef4fd0c6f8533e9e86a0c1f67` | `45ab73dafafca6841958a895795a29d2d9bfe789563194a7f84661f5aff634f9` |
| Windows | `12865626450` | `4ba5e8ae4869f10978d82a8943657d3be26e870164b027899e1422dc693da20a` | `3f381b9892939eb08e8ad462ccf38e924365d0cc44880656eefafa9c758fd836` |

The two independent source-pinned reports agree exactly on all authentic observed events, 16 original native FIT updates, output bit mapping, true terminal label values, all eight frozen source DEV predictions, all five model/control metrics, original ring parameter/checkpoint hashes, and source-admission NO-GO conditions. **Native original `LocalTaskRuntime` checkpoint/parameter SHA-256 differ across OS** despite equal displayed predictions/metrics, consistent with minor numerical/serialization differences; this is not byte-exact native cross-OS custody. Its serialized native checkpoint sizes were **1,207 bytes Linux and 1,206 bytes Windows**. The ring's original 604-byte checkpoint SHA-256 is identical on both OSes: `e68d1524533b703f3eabb61741ea7093317c7e4630c87cd7fba2d1086397a4f4`.

## Gate disposition and practical next work

**AC-19 engineering result:** an injective, locally accessible public observation/action/consequence representation can drive the original historical native eight-cell runtime *without* changing the original world or native model source, and source-bound frozen inference/checkpointing works cross-platform. The previously detected original full bridge type mismatch remains an independently evidenced **NO-GO**; do not claim it is repaired in the original historical repo or available in the current active branch.

**AC-19 scientific NO-GO:** No native agent performed actual source-directed actions; no realized on-policy reward, interactive adaptation, true A→B learning→A retention, unknown-family transfer, or autonomous model improvement was measured. The model did not outperform all matched controls. No code, branch, owner authority, native runtime, FORGE controller/queue, original scientific first-use, protected main or FSA acceptance was changed. Do not promote the result to Wingless/Yggdrasil or FORGE scientific selection.

**Next useful gate:** Scope a small, owner-authorized public-only **source-operated on-policy** check where the original source legally accepts the native model's action choices, with full two-stage public observation/consequence identity and true FIT/DEV separation. A model whose third action is not legal, whose on-policy checkpoint is not sealed, or whose family custody is unverified must abstain. Before new experiments, reconcile the historical eight-cell candidate with the *current active Ygg* owner and the already recorded FORGE issue #1031 negative. Performance is a development hypothesis only, not an autonomy milestone.

`AC19_AUTHENTIC_SOURCE_PUBLIC_ENGINEERING=PASS_BOTH_OS`  
`AC19_EXACT_TERMINAL_AND_REWARD_VALUES_PRESERVED=TRUE`  
`AC19_ORIGINAL_LOCAL_REWARD_CELL_PUBLIC_CONTEXT_VISIBLE=TRUE`  
`AC19_ACTUAL_NATIVE_LEARNER_AND_LOCAL_COUNT_FITTED=TRUE`  
`AC19_ORIGINAL_FULL_NATIVE_BRIDGE_ADMISSION=NO_GO`  
`AC19_SUPERIOR_TO_ALL_MATCHED_CONTROLS=FALSE`  
`AC19_NATIVE_ON_POLICY_INTERACTION=NOT_MEASURED`  
`AC19_SCIENTIFIC_FIRST_USE=FALSE`
