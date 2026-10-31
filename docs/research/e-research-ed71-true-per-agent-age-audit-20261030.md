# E-D71 — True per-agent observation-age verification (2026-10-30)

**Engineering replay PASS; model performance comparison NOT COMPLETED.**

Instrumented retained E-D69 executable in local container at `/mnt/data/e_research/ed69/audit_ed69.py`. The new read-only local probe `/mnt/data/e_research/ed71/run_ed71.py` replaces trace capture with tuple `(time,agent_id,selected_state,selected_action,time-last_time[agent_id],last_seen_state)`, then trains the same tabular Q baseline and extracts six original fixed tapes (seeds 43000–43002, clustered/sweeping resource conditions). For each decision it counterfactually queries the same Q values under cached last-seen cue, discrete 0.94^actual_age decay and 0.97^actual_age persistence. No environment rewards under alternative action choices were simulated.

| Measured check | Count |
|---|---:|
| Recorded masked decisions | **1,850** |
| Exact reference cache actions reproduced from Q table | **1,850/1,850** |
| Actual per-agent observation age differing from E-D70 t−19 approximation | **0** |
| Cache vs 0.94 decay action differences | **1,722** |
| Cache vs 0.97 persistence action differences | **1,634** |
| 0.94 decay vs 0.97 persistence action differences | **121** |

The zero age mismatch is an empirical property of **these six traces**, not a general guarantee for other environments or longer episodes. This closes the previously acknowledged timestamp uncertainty for E-D70's exact tape, but **does not** convert the counterfactual choices into rewards or establish a trained recurrent model. The 0.97 persistence remains a hand-coded heuristic; no trained recurrent baseline was run. No scientific first-use or native Wingless/Yggdrasil learning claim.

Local experiment and result bytes: `/mnt/data/e_research/ed71/run_ed71.py` and `/mnt/data/e_research/ed71/results.json`. Local files are not independently custodied in FORGE. The FORGE draft PR is advisory; no owner/controller/autonomy changes.

**Next gate E-D72:** construct and qualify a genuinely trained recurrent controller with matched observation/action/resource budgets, then compare held-out full-episode rewards against the tabular TD/cache/decay and conventional controls. Preserve original-source/scientific witness boundary.
