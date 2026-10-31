# E Research E-C15 — viability-extended spatial selection diagnostic (2026-10-29)

**Status:** Engineering FIT PASS; evolved construction benefit **NOT SUPPORTED**. Original execution was isolated local Python, not a FORGE-run CI/FSA scientific experiment. No selection, controller, owner or native-model change.

## Executed experiment

Reused the original 20×20 spatial niche-construction environment and same source policy definitions from E-C7, changing only the FIT evaluation horizon from 100 to **160 steps**. Six existing FIT seeds 41000–41005, four arms = **24 new evaluation trajectories**, plus the E-C7 candidate training episodes and replay. Arms: two-candidate selection allowing construction; same selection with construction disabled; fixed reactive constructor; greedy no-builder.

This is a **longer-horizon E-C7 diagnostic** and not yet the E-C15 full intended independently evolved intergenerational transfer experiment. The existing source includes spatial resource renewal and energy-limited births (cap 8), but the construction policy receives only two candidate policies, and fixed comparator arms do not receive matched training. This is reused development data, not first-use science.

| FIT arm | Median harvested | Median constructions | Median births | Median actions | Median survivors |
|---|---:|---:|---:|---:|---:|
| Evolved construct | 49.92 | **0** | 2 | 1230 | 8 |
| Evolved no-construction | 49.92 | 0 | 2 | 1230 | 8 |
| Fixed reactive constructor | 44.20 | 103 | 2 | 1147.5 | 7.5 |
| Greedy no-construction | **52.38** | 0 | 2 | 1230 | 8 |

All simulation assertions and replay **PASS**, maximum resource/energy accounting residual `2.5579538487363607e-10`. Local total wall ~1.65 seconds, process peak RSS ~96,280 KiB (not independent resource qualification).

**Scientific interpretation:** Even when the ecological horizon is increased enough for all evaluated policy classes to reproduce on development medians, the evolution-selected construction-enabled policy takes **zero construction actions** and matches its construction-disabled ablation. The greedy nonconstructor still outperforms it. An explicitly programmed constructor pays construction cost and underperforms the greedy no-builder. This is **no evidence that construction decisions evolved**, no newly discovered cognition or unanticipated transfer. Current FIT controls are not search/interaction matched.

## Source and raw result identity

- Original reused dependency `/mnt/data/e_research/ec7/run_ec7.py`, SHA-256 `04c81eaaa599030824f789a485359c1ea1d7c0335928481e7084ba4157be8375`
- New local wrapper `/mnt/data/e_research/ec15/run_ec15.py`, SHA-256 `c4ffdd74275cd929376293b3ff6ecb9f70309fa3b7e7ea2c06d5dd198b49dca3`
- Local raw `/mnt/data/e_research/ec15/results.json`, SHA-256 `87c5acbd4b7a1fb9d8be3c8c51ebf5e7435d205a1fd83a6392a54eb43be6d381`

These executable and raw bytes remain outside this **documentation-only** commit. Hashes are lookup candidates, **not independently authenticated evidence custody**. No independent FORGE CI, sealed first-use, full matched budget or scientific acceptance.

## Gate decision

**E-C15 diagnostic PASS / evolutionary construction claim NOT SUPPORTED.** Do not repeatedly adjust the current habitat reward. Next E-C16 should be a bounded **hypothesis feasibility audit**: before further evolution, establish that random, fixed and reactive policies can access a genuinely beneficial construction niche under *cost-matched* resources and no future-information leakage. Only thereafter, with approved immutable source and predeclared FIT/VAL/HOLDOUT, test evolving choice and unfamiliar transfer. If construction has no net benefit under sensible matched conditions, close this ecology instead.

Plain English: The organisms survived and reproduced, but evolution still chose not to build. Keeping them alive longer did not make them learn useful construction.
