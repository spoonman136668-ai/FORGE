# E-D127 — Authenticated original MiniGrid Memory random-action baseline (2026-10-30)

**Engineering execution PASS; random policy success 0/4; scientific learning/first-use NOT ACCEPTED.**

Original authenticated GitHub Actions run [41128025114](https://github.com/spoonman136668-ai/FORGE/actions/runs/41128025114), Linux job `124312395415`, source branch PR #1194 head `b3ba1927ef7cc6606bd269660cf4db5d4ab8aca6`. Original environment `MiniGrid-MemoryS13Random-v0`, MiniGrid `3.2.0`. Reused E-D84 *engineering smoke seeds only* `84000`–`84003`, not FIT/VAL/DEV/holdout. Policy is deterministic per-seed uniform-random actions with a 128-action cap, repeated seed runs checked against exact trace SHA-256. This is a deliberately weak control, not a trained policy or fair conventional memory baseline.

| seed | actions | reward | terminated | truncated | budget_exhausted | replay trace SHA-256 |
|---|---:|---:|---|---|---|---|
| 84000 | 128 | 0 | false | false | true | `ab1c73069f6875d9e35703f2b22ebab9ad80216d0c9fc019a64fa1356b06406e` |
| 84001 | 84 | 0 | true | false | false | `4c4a2ea3b8a6b7aeb6b669b4a43bcbcd88fd0de1fc23f3616bdeddab3b3b06e8` |
| 84002 | 84 | 0 | true | false | false | `504a2c64c83adf8d6498440f5babb04f1588be9519a283b54cec550d7fe391ab` |
| 84003 | 128 | 0 | false | false | true | `64066f8995c68bbd8cd1ccc75b318e92bc4adb4269a5c5c7d9b8f9c4ec59a81c` |

Mean actions = (128+84+84+128)/4 = **106**. Success/reward >0 count **0/4**. An episode ending with reward 0 is not evidence of correct matching; it can reflect a wrong object. End at 128 actions is a *local policy budget* termination, not `env.truncated`. Do not overclaim reward 0 means absent learning; this baseline has no learning by design.

The Linux job completed `success` including original Memory smoke, E-D125 random baseline, F139, Go tests, race, vet, build, and isolation. Windows job was in progress when accessed; final workflow check remains separate.

**Research caveats:** Four reused exposed seeds are inadequate for reliable population success estimate, not an independent frozen cohort, no training, no native Wingless/Yggdrasil, no memory-specific control, no matched information/resource fair comparison, no cold restart retention, no unfamiliar-family transfer, no independent FSA scientific first-use. No production changes.

**Next meaningful scientific step:** select/qualify an interpretable memory-dependent non-oracular reference agent using visible observations only; measure positive success on *engineering exposed seeds* before frozen FIT/VAL/DEV comparisons, respecting pending authorization and source custody. Do not consume sealed holdout or alter FORGE autonomy.