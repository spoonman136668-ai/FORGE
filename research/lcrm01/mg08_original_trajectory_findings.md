# MG08 — Independent MG07 source trajectory findings (read-only)

**Source custody.** Original FORGE PR #1077 at `a8a7a2e01c51c1676d39ab9a7a46c91dfee78c24`, GitHub Actions run [40801439498](https://github.com/spoonman136668-ai/FORGE/actions/runs/40801439498), artifact 12865848091. Both full original-source processes agree on canonical SHA-256 `5bc45932b8dcc8ed96909833550e0d07afb45c03e3a570d9e2ff15400d102c47`. This is source-authentic development evidence only.

Each actor completed 3 episodes of 192 *own-selected* original Farama DoorKey actions, with **zero** live external fallback. The following numbers were independently computed by reading all 15 original public before/action/after event sequences from the archived first.json and recomputing the original public pixels at `image[3][6]` (held key) and `image[3][5]` (front door).

| Original source-public measure / 576 actions per arm | Wingless DK10 | Wingless DK9 | Yggdrasil R14 | Yggdrasil R13 | Conventional temporal |
|---|---:|---:|---:|---:|---:|
| Distinct views, summed within resets | 138 | 53 | 93 | 55 | 83 |
| Repeated views, within each reset | 438 | 523 | 483 | 521 | 493 |
| Key pickups | 49 | 7 | 2 | 0 | 1 |
| Key drops | 46 | 6 | 2 | 0 | 1 |
| Source-public steps already carrying a key | 370 | 24 | 5 | 0 | 4 |
| Forward action while visibly carrying key | 37 | 0 | 0 | 0 | 0 |
| Door visible anywhere while carrying key | 204 | 0 | 3 | 0 | 4 |
| Door directly in front while carrying key | 0 | 0 | 0 | 0 | 0 |
| Original source door opens | 0 | 0 | 0 | 0 | 0 |
| Original positive goal rewards | 0 | 0 | 0 | 0 | 0 |

**Falsifiable findings.** Wingless DK10 has broader public-state exposure and some forward actions during key carriage, but 49 pickup and 46 drop transitions show substantial key-handling cycling, not productive independent object navigation. Yggdrasil R14 increases distinct views and records two pickups followed by two drops, but never moves forward while carrying a key. No arm achieved a key-carried door-front condition or opened an original door. These are results on exactly three development seeds, not inferential generality.

**Important input-parity caveat.** MG07 evaluator line `wing.request("choose",before=before,objective=original.objective(owner,before))` supplies both Wingless Go arms an **externally authored, public-derived stage objective** (`carrying_changed` versus `visible_door_state_changed`) in addition to the raw public observation. Yggdrasil R13/R14 and conventional do not receive an equivalent explicit objective argument in the MG07 evaluator. Thus the original public images/actions may be matched, but the *policy-facing derived information* is not strictly identical. This is not hidden source state or a proven unfair outcome, but must remain disclosed and separately ablated before any claim of native architectural superiority.

**Prospective next learning gate.** Remove externally authored stage-objective asymmetry; independently learn and retain source-public action-consequence chains beyond a single step, with bounded memory. Prespecify identical original-source observations, equal FIT events, true online own-selected feedback, conventional memory-equipped comparator, unmodified parents, and all seed/resource budgets. Require observed progression from key pickup through sustained carrying, forward navigation, door contact, door opening and true reward. Negative results remain negative, and no manually coded DoorKey action sequence may be used.

**Authority.** This finding does not rerun an original episode, open a sealed holdout, alter either native implementation, merge research, dispatch FORGE/CKB controllers, waive Atlas/G29, or claim scientific first-use.
