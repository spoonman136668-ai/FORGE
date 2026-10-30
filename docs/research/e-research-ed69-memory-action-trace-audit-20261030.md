# E-D69 — Instrumented observation-memory action divergence (2026-10-30)

**Local diagnostic execution PASS; scientific benefit of decay NOT demonstrated.** Instrumented corrected E-D68 controller (source SHA-256 `9e5dbbeecf1b97ccdf00d428a9df21cd9bb540fc002468fad104ab3b6222745b`) to record each masked action's discrete observation state and action. Reused trained Q policy for paired last-cache versus decay; matched 3 seeds 43000–43002, clustered and sweeping resource shifts, 40-step masks, six matched comparisons. E-D69 execution source `/mnt/data/e_research/ed69/audit_ed69.py` SHA-256 `cfa5814d83f2f07f966cd61a872515a3446d1c0410639ba22301e94b5e1f28a5`; result JSON SHA-256 `383eb7af226bbcf2dee58fadf35c892ecfd9a3eb05156548d65c2151c6979b85`. Original bytes **remain local; GitHub contains only this advisory summary**.

| Seed | Shift | Matched time/agent decisions | Different cue states | Different actions |
|---|---|---:|---:|---:|
| 43000 | clustered | 393 | 393 | 382 |
| 43000 | sweeping | 401 | 401 | 357 |
| 43001 | clustered | 204 | 204 | 193 |
| 43001 | sweeping | 230 | 230 | 208 |
| 43002 | clustered | 192 | 192 | 192 |
| 43002 | sweeping | 226 | 226 | 186 |
| **Total** | | **1646** | **1646** | **1518** |

92.22% disagreement in actions across matched (time, agent-index) decision records, and distinct cue states for all 1,646 matched records. This verifies that E-D68 decay is no longer E-D67's no-op. Counts for paired runs differ because the two policies drive different trajectories and agent survival; these matches **are not identical underlying physical states** and therefore cannot isolate direct causal action effects. The diagnostic instrument adds only trace recording; it uses the identical E-D68 E-C2 synthetic environment, source-pinned local modules, frozen evaluation and Q updates confined to training.

**Disposition:** Mechanism difference confirmed, but no demonstrated superior belief decay, generalized memory or native emergent intelligence. E-D67 decay equality was caused by a harness bug and stays invalidated. Next: enforce a trajectory-coupled teacher-forced common observation-state sequence to isolate policy mapping differences, then independent recurrence/belief baseline and holdout if access permits. No scientific first-use and no FORGE production/autonomy change.