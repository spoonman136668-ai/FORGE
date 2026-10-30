# E Research E-D17 — learned value-of-information probe selection FIT (2026-10-29)

**Status:** engineering FIT PASS; context-dependent information purchasing improves task net reward; novel causal intelligence advantage **NOT SUPPORTED**. Documentation-only advisory, no FORGE autonomy/controller/owner/model selection/scientific acceptance mutation.

## Actual isolated CPU experiment

The environment has a hidden binary structural change between two paid interventions. An optional costly binary probe reports the change correctly with one of three public reliability classes (55%, 80%, 95%). Probe costs are 1, 3, or 5 energy; two gate interventions each cost 4 energy and one unit of material, and 12 units are harvested only after both successful interventions. There is no reward for buying a probe or constructing a barrier. Source of initial-gate action is **hardcoded correct** for all arms, explicitly a simplifying assumption rather than learner achievement.

Training: **18,000 local interventions** (6,000 seeded encounters per reliability class). Probe reliability empirical agreement (correct / 6000) was 3359/6000 for nominal .55, 4783/6000 for nominal .80, and 5714/6000 for nominal .95. The learner uses these empirical rates in a **programmer-specified expected value of information formula**: buy when 12*(estimated probability correct -.5) exceeds probe cost. The Bayesian conventional control uses the known generating likelihood in the *same* formula. Thus policy optimization is not emergently learned end-to-end; the **precision is learned, selection calculation is authored**. Other controls: always-buy, never-buy, random-buy, and scrambled-signal paid probe.

Evaluation: 240 development seeds x three reliabilities x three costs x six policies = **12,960 trajectories**. Every policy has identical action costs and physical resource budget; probe use is a policy decision and incurs its actual expense. Same public reliability/cost labels and decision opportunities. Simulator bookkeeping: starting energy 20, two material units; after two builds plus optional probe energy remaining equals initial energy minus paid costs, material remaining zero. Assertions and exact full-seeded replay PASS. No independently sealed validation/holdout. All environments still use the same binary source model as E-D16, not unfamiliar transfer.

| Policy | successes /2160 | probes /2160 | mean harvest minus energy spent |
|---|---:|---:|---:|
| Empirical learned-precision VOI | 1578 | 1200 | -0.6778 |
| Conventional Bayesian known-precision VOI | 1578 | 1200 | -0.6778 |
| Always buy | 1647 | 2160 | -1.85 |
| Never buy | 1107 | 0 | -1.85 |
| Random buy | 1383 | 1122 | -1.8648 |
| Always buy scrambled signal | 513 | 2160 | -8.15 |

The VOI controls decline probes for low precision (55%) and high cost; the empirical learner matches Bayesian decisions on all 9 scenario cells. **No advantage over standard Bayesian value-of-information selection is observed.** All policy mean net rewards are negative under this model; optimized probing only makes them *less negative*. At source conditions, knowledge of reliability is publicly provided as a class label. This is not evidence the agent independently identified uncertainty classes or invented active sensing.

### Custody / verification limits

Actually executed Python: `/mnt/data/e_research/ed17/run_ed17.py`, SHA256 `21fa0a9b7141a775497309e01a611eff5285dcdcf73169ce57bf80a8851cb221`.
Raw evaluation and training digest JSON: `/mnt/data/e_research/ed17/results.json`, SHA256 `1b4816cfa9f74305311f5733611437c83c61d4d5b614ff0c9b6b4b11fef8be2e`.
Replay PASS, ledger PASS, wall ~0.665 sec, peak RSS ~104972 KiB (process-level, not independently qualified).
These original bytes remain outside this documentation-only GitHub commit; only report is remotely preserved. No independent native FORGE FSA qualification, sealed experiment provenance or first-use witness. Do not promote to model acceptance.

### Decision and next gate E-D18

Learning probe reliability matters, but the *decision algorithm* is a hand-coded VOI threshold that simply matches a conventional Bayesian controller. E-D18 should require an adaptive strategy to **discover** reliability/cost tradeoffs, including unknown/drifting precision, multiple possible probes and competing observation opportunities, then compare sample efficiency and net reward to Bayesian belief-state, UCB/contextual bandit, and fixed policies under equal feedback and total decision budgets. Fit and validate on disjoint predeclared source families and freeze truly independent holdout before claims. If standard controls dominate, preserve the negative instead of tuning toward a narrative.

**Plain English:** The agent learned how reliable the clue was and only paid for it when worthwhile. This reduced losses, but ordinary Bayesian reasoning made exactly the same choices.
