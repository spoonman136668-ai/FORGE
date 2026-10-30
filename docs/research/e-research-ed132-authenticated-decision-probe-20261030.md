# E-D132 — Authenticated MiniGrid cue-decision probe; behavioral advantage unproven

GitHub Actions run **41130486371**, Linux job **124320949733** and Windows job **124320950143** both succeeded at draft PR #1194 commit `f0cd0c6872c807512b82aaff06942983f361f790`. The Linux log prints `PASS_ENGINEERING_CUE_DECISION_PROBE` from `research/e_research/ed131_cue_decision_probe.py`, on exposed smoke seeds only, not scientific FIT/VAL/DEV/HOLDOUT.

| Seed | Frames | Comparable frames | Decisions differ | Blind frames | Ambiguous observation | Decision trace SHA256 |
|---|---:|---:|---:|---:|---|---|
| 84000 | 4 | 2 | 2 | 0 | true | `91ee97d0e75e9a24cd7d92f23c412dee67e35b90b0fccd435e2f9e73da206101` |
| 84001 | 13 | 6 | 6 | 0 | true | `feca4f70fe87a456b82f403df11f4db99ff57ff79997a81f164d76168795e3c4` |
| 84002 | 13 | 4 | 4 | 0 | true | `584cb42df1a69b9f3380669bcb15d2aa04250efc421509cf6f94570b34bae7e0` |
| 84003 | 8 | 4 | 4 | 0 | true | `6fd85cb0e4426e52d20635baf20a115e2562396276b5fb8bca0efa280c031230` |

**Causal caveat:** The memoryless rule is hardcoded to predict 0; the memory rule compares current unique visible cue against the earliest unique visible cue. That first cue is not established as the task's starting-room cue, and the two rules are not behaviorally exercised. A decision difference is not an accuracy measure. `blind_frames=0` under this detector's definition, despite earlier E-D130 finding 10/38 retained-only frames using a different detector; the two measurements are not directly equivalent. The fixed action script generated rewards, including positive reward for seed 84001; no policy was controlled by the cue register. No learned model, native Wingless/Yggdrasil integration, independent frozen cohort, scientific first-use, or FORGE autonomy changes.

**Scientific decision:** Engineering PASS, behavioral claim UNVERIFIED. A later proper comparison must isolate visible original cue before movement or explicitly declare cue unobservable; distinguish cue state, navigation, and reward, with identical observation/action/resource budgets. Keep holdout sealed and draft branch isolated.