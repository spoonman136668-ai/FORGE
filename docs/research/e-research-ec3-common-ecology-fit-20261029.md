# E Research E-C3 — common-ecology FIT comparison (2026-10-29)

**Status:** FIT execution PASS; dynamic training advantage UNVERIFIED; **resource/interaction parity incomplete**. Advisory only; no native FORGE execution or scientific acceptance. No files were delivered to user's Library.

## Actual execution

Reused the original E-C2 script at session SHA-256 `1b3159224711ba46c4ef847fcce7ec1eff06ac6cd76e87d912461bf3cbe78154` and imported it via a bounded local wrapper (`/tmp/ec3.py`). The only behavioral modification was that **evolve_static** receives the SAME dynamic ecological episode generator during evaluation as **evolve_dynamic**; training remains static for the former. Four arms, FIT seeds 31000–31011, nominal 80-step evaluation = **48 evaluation arms**, with existing 3-generation training routine. No independently frozen HOLDOUT. E-C2 selection rule was unchanged; **stronger selection was not implemented** in this gate.

Original E-C2 agent type, reproductive energy splitting, mutation and zero-energy inactivity retained. Deterministic replay of one paired seed PASS, maximum resource-energy ledger error `1.6443e-11`. Fully matched *nominal step count* and test ecology but **effective organism-action counts differ**; no valid equal-interaction advantage conclusion.

| Arm (common dynamic eval ecology) | Median harvested | Median actions | Median harvested/action | Median births | Median survivors |
|---|---:|---:|---:|---:|---:|
| Evolve on dynamic | 3.2075 | 472.5 | 0.0069323 | 0 | 4 |
| Evolve on static | 3.0690 | 453.5 | 0.0066101 | 0 | 3.5 |
| Random-parent, dynamic | 0.4750 | 241.5 | 0.0019415 | 0 | 0 |
| Greedy reactive, dynamic | **26.7000** | 859.5 | **0.0311012** | **6** | **12** |

These are medians of seed-level ratios, not ratios of aggregated medians. Paired dynamic-minus-static per-seed harvested/action differences: `[0.00016614,0,0.01897833,0,0.00123949,0.00338472,0.00675532,-0.00066634,0,-0.00013730,-0.00032211,0.00014030]`. Positive 6, negative 3, zero 3, with one prominent positive outlier; not qualified evidence of a consistent advantage.

**Conclusion:** A single matched *evaluation ecology* reduces the confounding found in E-C1/E-C2, but does not establish equal interaction budgets, an evolution gain over competent reactive behavior, or novel transferable capability. The greedy control still outperforms evolving agents. No statistical claim or source/first-use acceptance.

## Evidence custody

Execution wrapper and raw JSON exist at `/tmp/ec3.py` and `/tmp/ec3_results.json` only in the isolated current session. This GitHub document does not include source or raw JSON, and no independent FORGE original evidence custody, CI replay or scientific witness was performed. The original E-C2 source was read at the SHA-256 above, not pinned to a Git commit. **Repository-only reproduction UNVERIFIED.**

## Next gate E-C4

Implement actual *equal organism-action budget* evaluation with one shared dynamic environment schedule across all arms (including greedy); separately track survivorship-censored runs, births, resource replenishment, and total wall/CPU/memory. Use source-pinned controls and a matched strong policy-search baseline rather than treating random parents as sufficient. If still dominated, terminate this ecological setting and try a qualitatively different coevolution mechanism instead of budget-intensive tuning.

**Plain English:** Making the test world the same for both evolutionary arms does not produce a convincing advantage. Greedy behavior still wins. Population action counts differ, so the next test must fix that comparison before interpreting results.
