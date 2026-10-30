# E-D130 — Authenticated visible-cue retention diagnostic (2026-10-30)

**Original official MiniGrid engineering execution PASS. Retained-only visible cue information observed. Behavioral benefit or learned intelligence NOT DEMONSTRATED.**

Authenticated GitHub Actions [run 41129377167](https://github.com/spoonman136668-ai/FORGE/actions/runs/41129377167), completed Linux job `124316927685` (success), draft PR #1194 commit `37328394f60e44a1f681d8e1a6e79aae99fcedc3`. The existing isolated research workflow invokes `research/e_research/ed128_visible_cue_retention.py`, against official original `MiniGrid-MemoryS13Random-v0`; exposed engineering smoke seeds only.

| seed | observed frames | visible-cue frames | retained-only frames | final reward | exact trace SHA256 |
|---|---:|---:|---:|---:|---|
| 84000 | 4 | 2 | 0 | 0 | `eaea2c4906cb34d2390251ce1c7577952bbb4eea1e09ab37537eb6c114ab89df` |
| 84001 | 13 | 6 | 5 | 0.9872189349112426 | `e4fc1127a1f49d90805fb834273f6cbec853b267a82ab368966f01cc6de130d7` |
| 84002 | 13 | 4 | 3 | 0 | `dc3a9052094c2eb6f6afc5ede5c84dde2f879a33ca59a4ae1260caf2520d6cf0` |
| 84003 | 8 | 4 | 2 | 0 | `b0c9a4465ea136f0edd281a942d9b2337b3f5128af5aca0fb51d0e002c2cb932` |

Total retained-only frames 10/38; positive on three of four **exposed** trajectories. Deterministic replay equality is asserted per seed. Each replay follows a fixed scripted set of actions, identical to its memoryless comparison. The cue detector stores the most recent unique object from partial RGB-independent object encoding and may update with later sightings: it does NOT guarantee retention of the *original start-room cue*, which is a scientific limitation for the true matching-object task. One script achieves positive reward by preselected actions, NOT because a memory register controlled its actions. No evidence that remembering improves policy success, no learned internal state, no cold restart retention, no unseen-family transfer, no native Wingless/Yggdrasil training, and no independent first-use authority.

**Scientific decision:** Engineering positive only. A proper next behavioral comparison needs a provenance-bounded policy that stores the initial cue, controls navigation from observation with matched actions, compares memoryless and memory policies under identical source, training, and compute budgets on exposed engineering cases; keep sealed FIT/VAL/DEV/HOLDOUT untouched until approved. The overall Windows job was still in progress at the time of initial query; do not infer workflow success from Linux alone. No FORGE autonomy/controller changes.
