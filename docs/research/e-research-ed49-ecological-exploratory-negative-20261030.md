# E-D49 — Exploratory ecological adaptation transfer probe (2026-10-30)

**Execution: PASS. Scientific enhancement claim: REJECTED / NOT DEMONSTRATED.**

Reused the existing E-C2 session-local Python ecological model **without changing its policy functions** and tested four policy arms over 12 previously unused exploratory seeds **32000–32011**. Experiment source at `/mnt/data/e_research/ec2/run_ec2.py`, SHA-256 `1b3159224711ba46c4ef847fcce7ec1eff06ac6cd76e87d912461bf3cbe78154`. Executed test script `ed49/run_ed49.py`, SHA-256 `50063925dfad49c2c1a768b42c7d3a299350d64c16e885d29ea6204130af557c`. Output `ed49/results.json`, SHA-256 `c5645afd736412523a4b9650eab4f2ec625486ab62c9999b0a23988666165545`. Original execution files remain **session-local**; their hashes are identifiers, **not independently authenticated custody**. This record retains the observed summary but does not claim original data bytes were uploaded to GitHub.

## Engineering results
48 trajectories (12 seeds × 4 arms); rerunning the entire set produced identical Python result objects (replay PASS). Max within-episode energy ledger residual: `1.7352341785681347e-11`. Runtime approximately 14.1 s.

| Policy | Mean harvest/action | Median harvest/action | Median births |
|---|---:|---:|---:|
| evolve_dynamic | 0.00987730 | 0.00653880 | 0 |
| evolve_static | 0.01514837 | 0.00857946 | 0 |
| random_parent_dynamic | 0.00651204 | 0.00409587 | 0 |
| greedy_dynamic | **0.03129854** | **0.03258168** | **6** |

Paired evolve_dynamic differences (per-seed mean, wins/ties/losses): versus random parent `+0.00336526`, **6/3/3**; versus static evolution `−0.00527107`, **4/1/7**; versus greedy `−0.02142124`, **0/0/12**. Greedy's mean harvest/action was ~3.17× dynamic evolution's, and won all 12 comparisons.

## Scientific interpretation / boundaries
**Negative:** No persuasive competitive autonomous adaptation. Greedy dominates all 12 seeds; the modest exploratory difference against random-parent is not independently validated and has ties and losses. No new genuine emergence, causal identification or transfer was demonstrated.

**Critical limitations:** E-C2 is a hand-designed local synthetic environment. These seeds are an exploratory FIT extension, **not a sealed holdout**. The comparison includes a greedy heuristic and evolutionary variants; it is not an accepted native Wingless/Yggdrasil learner-vs-trained-conventional benchmark. No source-pinned original external environment, independent witness, exact artifact custody in GitHub, or FSA scientific first-use authorization.

**Disposition:** Preserve as advisory negative evidence only in draft PR #1194. Do not promote to FORGE research selection as a validated scientific result. DoorKey remains independently BLOCKED on an Actions-capable runner (issue #1245), with no new activation changes required.
