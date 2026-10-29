# AC-19 — Lossless typed original DTR → historical Ygg eight-cell runtime bridge

**Frozen development-only protocol. No new original DTR episodes, active native-branch mutation, controller dispatch or first-use.**

## Motivation and exact source identity

AC-18's [qualified Linux/Windows run #40797373953](https://github.com/spoonman136668-ai/FORGE/actions/runs/40797373953) showed an original historical Ygg `NativeRingMemoryDev` could fit 16 real public DTR action–reward transitions but lost to a conventional acting EMA (heldout 4 terminal rewards Brier proxy 0.395318 vs 0.232666). The original historical *full* `NativeTaskRingBridgeDev` cannot accept original source reward 1 or terminal successor `None`; its declared fixed reward categories are `(-3,0,10)` and it requires a non-null successor observation. Source values must **never** be silently relabelled.

Source-pin original Causal-Gymnasium DTR commit `c94e9a4cd3641588b6b8507e71ccee5c27032bdf` and the actual prior AC-15 public FIT 8 episodes (16 stage transitions), frozen DEV 4 episodes (8 stage transitions). AC-19 revalidates the AC-15 source JSON and AC-18 no-first-use receipt, creates **zero new source events** and uses no source oracle or privileged `info`/latent `u`.

Pin the original historical Ygg development commit `a39171a76d0d7817e3563682bb139a9d7ecf37c4`, `yggdrasil/task_runtime.py` Git blob `68a1423e0bd7206af511212c14b6ce8534154cc2`, `itd02_local_ring_memory_dev.py` blob `1db0835d5c99456bcf99a013d4836f49314a9d39`, `itd02_native_task_bridge_dev.py` blob `b311ea7ea00c15d23e7bd43ff97bd10ce3d8b87c`. It is historical development source, **absent from current active Ygg `92c421a5475a27015a390efb88c373eb5f15379d`**. No source edits or import substitution; original unchanged `LocalTaskRuntime.observe/predict/snapshot/restore`, original unchanged `NativeRingMemoryDev.feedback/checkpoint/restore` operate underneath an **external typed adapter**.

## Reversible eight-site code

Separate read-only fixed adapters encode *before* and *after* as original validated binary eight-cell arrays, not fixed semantic reward laws:

- `before(stage, public_bit, action)`: one-hot sites **0..3** encode all four exact stage×bit contexts, one-hot sites **4..5** encode action 0/1, sites 6..7 zero. Original `LocalTaskRuntime.predict` sees only the public tuple; no next observation or reward leak.
- `after(next_observation, terminal, reward)`: sites **0..2** one-hot next public bit 0, bit 1, or terminal `None` (distinct reserved category); site **3** is exact terminal flag; sites **4..5** one-hot real binary reward 0/1; sites 6..7 zero. The terminal sentinel is an adapter representation of an **actual source null**, not a fictitious environment successor. A strict inverse checks both one-hot regions, terminal/null consistency, zero reserved sites and rejects invalid values.
- Check exhaustive injective round-trips for every legal staged public input and output; no category of reward 1 is mapped to original native reward label 10 and the original historical `NativeTaskRingBridgeDev.public_outcome` still rejects direct original terminal data.

## Native model execution and controls

Use **one original** `LocalTaskRuntime` and **one original** eight-cell `NativeRingMemoryDev` on exactly the source-scripted transitions. On FIT, original native `observe(before_bits,after_bits)` updates local genome and roles, and original ring `advance(public_observation)` followed by `feedback(fixed_original_action,actual_source_reward, learning=True)` updates local retention/action heads; sixteen actual transitions/updates per component, no DTR policy actions.

An independently FIT-trained *original* `LocalCountControl` receives **identical** 8-bit before and after labels and is scored at target cell5 for terminal source reward1. Also retain previous AC-18 matched source history/action fitted tabular, acting EMA and pooled prior on the same FIT terminal source rewards. Native score at output site5 is a model probability from sigmoid; original ring score is an uncalibrated Q proxy and is NOT fused or promoted. No tuning on DEV. Frozen original runtime and ring state must survive original `snapshot/restore` and `checkpoint/restore`; compare exact original native cell/role parameter identity and ring identity, all eight frozen DEV predictions and all source outputs across OS, while preserving zero DEV training and zero newly executed DTR episodes.

Compare native `LocalTaskRuntime` output-bit probability and equal-information `LocalCountControl` cell5 probability against actual held-out 4 terminal source rewards using accuracy/Brier; include fitted history tabular, EMA and pooled controls. Stage0 public successor and reward must be encoded losslessly but must not be falsely scored as a terminal reward. Record non-terminal/terminal counts, sampled legal native action scores and any model-only action choice explicitly as **off-policy**. A valid typed adapter, learned weights and checkpoint are **engineering** success only; no native/causal/retention superiority, real policy return, independent-cell plasticity or unfamiliar-family transfer without stronger held-out authentic trial and owner witness. No production full native bridge claim: external typed adapter is **not** source Ygg's original bridge API.

## Qualification

Scoped GitHub-hosted Windows + Linux PR workflow on existing FORGE draft #1062; reuse same source report, pin Ygg historical source, run original Ygg source tests, strict serialization/inversion guard tests and observed exact-source parity. A platform FAIL blocks qualification until a narrowly justified repair; preserve negative results. **Never** dispatch or modify F139, scientific witness, active Ygg/Wingless, original source files, current FORGE controller or protected main.

`AC19_SOURCE_NEW_EPISODES=ZERO`  
`AC19_REAL_REWARD_ONE_PRESERVED=TRUE`  
`AC19_TERMINAL_NONE_PRESERVED=TRUE`  
`AC19_ORIGINAL_NATIVE_LOCAL_TASK_RUNTIME=UNCHANGED`  
`AC19_EXISTING_NATIVE_BRIDGE_REPLACED_IN_PRODUCTION=FALSE`  
`AC19_SCIENTIFIC_FIRST_USE=FALSE`
