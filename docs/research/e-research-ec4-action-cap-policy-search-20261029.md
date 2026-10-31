# E Research E-C4 — capped-action ecology and policy-search FIT control (2026-10-29)

**Disposition:** Local numerical engineering PASS; **equal realized organism-action budgets FAIL** (extinction-censored); **evolutionary advantage NOT SUPPORTED**. Advisory, FIT-only. No FORGE native scientific first-use, FSA source custody, accepted-model change or autonomy interference.

## Executed implementation and protocol

Derived isolated Python stdlib `run_ec4.py` from session copy of E-C2 `run_ec2.py`. Existing 16×16 periodic ecology, 80-step episodes, 3 selection generations, resource/energy conservation, on-episode energy-splitting births retained. FIT seeds 31000–31005, five arms = **30 evaluation runs**, plus training episodes and deterministic replay. Evaluation of **all** arms uses the same seed-specified dynamic resource schedule and a maximum **300 realized organism actions**. A population can go extinct before 300; no free resurrection or forced continued actions.

Added **policy_search_dynamic** comparator: select the highest-training-harvest homogeneous four-weight policy from 18 randomly sampled candidates evaluated during 3 training generations (one six-agent episode per candidate). This receives a different, greater training search/interaction budget than the ordinary evolutionary arms: comparison is **diagnostic, not training-budget fair**. Original dynamic, static training, random-parent, and greedy controls retained. This model is *not* sophisticated evolutionary coevolution or evidence of within-lifetime learning.

## Executed FIT evaluation summary (medians over six seeds)

| Arm | Harvest | Harvest per realized action | Actions | Births | Runs reaching 300 actions |
|---|---:|---:|---:|---:|---:|
| Evolve_dynamic | 2.4975 | 0.0083250 | 300 | 0 | 5/6 |
| Evolve_static (dynamic eval) | 1.5335 | 0.0053871 | 272 | 0 | 3/6 |
| Random_parent_dynamic | 0.5350 | 0.0021617 | 249.5 | 0 | 2/6 |
| Greedy_dynamic | **12.1200** | **0.0404000** | 300 | **6** | 6/6 |
| Policy_search_dynamic | **9.6760** | **0.0322533** | 300 | 3.5 | 6/6 |

**Engineering checks:** Source-replayed first-evolve-dynamic row exactly, PASS. Conservation ledger absolute worst discrepancy **1.55455e−11**, resource and energy range assertions PASS, no forced repair. Elapsed wall ~3.53 s for bounded local script; not a full CPU/RAM qualification receipt.

**Qualification boundary:** The *cap* is common; **the actual realized actions are NOT equal**. Do not describe this experiment as equal-interaction scientific comparison. Per-action ratios are descriptive and suffer extinction selection/censoring; without matched training search, credible statistical uncertainties and unfamiliar-family transfer they cannot establish evolutionary advantage. Simple greedy remains clearly stronger, and the policy-search comparator improves over the ordinary evolving arms while receiving unequal training compute. No acquired cognition, novelty or transfer claim.

## Original-byte pointers and reproducibility limits

- Session source `/mnt/data/ec4/run_ec4.py` SHA-256 `d7764d0d46ac4f101a374a2e266d291df801352d0d6b7a9d6ea46913743962e7`
- Session JSON `/mnt/data/ec4/results.json` SHA-256 `f45a534bda99664fcf37d255d38d9b688031b483f6f0c3131895ccd8e1d19eb0`
- These bytes are **not included in the documentation-only draft commit**; reported hashes are identity pointers, not independently authenticated scientific source custody. No FORGE-run CI, held-out cohort, owner/witness clearance or scientific acceptance.

## Next eligible gate: E-C5

Either use a fixed number of **available decision opportunities with absorbing extinction outcome** as the primary, preregistered metric (without falsely requiring every dead agent to act), and **match total training candidate/organism steps** among evolutionary search methods; or terminate this ecology setting after a bounded diagnostic as not promising. Freeze an unfamiliar challenge family before validation; do not claim scientific transfer without independent first-use authorization. Preserve both negative results and exact artifacts under an approved custodian.

**Plain English:** We capped each trial at the same number of actions, but some populations died first. A standard greedy agent and a larger simple policy search still beat ordinary evolution. More tuning is not yet justified by evidence.
