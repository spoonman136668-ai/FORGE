# E Research E-D3 — reduced observation and two-barrier transfer FIT (2026-10-29)

**Engineering PASS. Unfamiliar two-barrier transfer NOT SUPPORTED. Scientific first-use/independent acceptance UNVERIFIED.** This is an isolated, newly executed local Python experiment; advisory only, no FORGE autonomy or native model modifications.

## Design

Actual script source derives the E-D2 tabular Q learning and fixed-policy world, with 9x9 fixed-height vertical barrier walls. Single wall at x=4 is training family; two walls at x=3 and x=5 require two paid local construction actions, and locked x=4 cannot be modified. Start/goal y coordinates seeded independently, never visible as a global wall map. Every action consumes one energy, construction additionally three energy and one material. Material budget is one for single/locked and two for double. Goal harvest reward is 8 only on reaching destination. 65-action horizon, energy 110. Offline BFS reachability evaluator is not fed into policy.

Two Q learners receive **identical training episode budgets** (260 loops × six seeds = 1,560 episodes each, 3,120 total), training **only on single-wall world**. Rich state stores absolute x/y, goal-relative vector and local wall occupancy; reduced state stores goal-direction signs and capped distance bins, material, adjacent wall/boundary occupancy, but no absolute x/y. Both use the same legal actions, Q learning and epsilon schedule. Fixed rule and greedy controls have no learning. Evaluation: 12 development seeds × three world classes (single, double, locked) × five policies = **180 trajectories**. Seeds are freshly chosen but **not sealed/independently held out**; this is a FIT development diagnostic, not scientific first-use or confirmed unfamiliar transfer.

| Policy | Single reached | Double reached | Locked reached |
|---|---:|---:|---:|
| Random | 2/12 | 0/12 | 0/12 |
| Greedy no-build | 0/12 | 0/12 | 0/12 |
| Preprogrammed builder | 12/12 | 12/12 | 0/12 |
| Q rich coordinates | 5/12 | 0/12 | 0/12 |
| Q reduced state | 11/12 | 0/12 | 0/12 |

E-D3 cannot infer statistical superiority of reduced observation without matched repeated learner seeds/confidence intervals; the reduced learner improved in these 12 cases. Neither learner transferred to the novel two-barrier problem. The builder is explicitly programmed to construct whenever a forward wall is adjacent, and solves both; this is a conventional positive control, not an upper bound on intelligence. The double wall is BFS-reachable, the locked wall BFS-unreachable. No cumulative adaptive experience within an evaluation episode; Q is frozen at evaluation.

**Engineering:** energy+spent=110 and materials remaining+builds equals one/two at every step PASS; exact rerun comparison of all 180 trajectories PASS; offline BFS feasibility checks PASS. Elapsed local script time 1.125 seconds, peak process RSS 97,800 KiB. Training action counts and true compute parity to a model-based learned planner were not measured.

## Provenance

Executed original script `/mnt/data/e_research/ed3/run_ed3.py` SHA256 `1b107b3a249cfd00f2818b720fd11391479149274bbbd107e47efefbfb8bb3d1`.
Raw complete JSON `/mnt/data/e_research/ed3/results.json` SHA256 `771a0c36388900d04ad3046ad49df8c3064dda1fe0d51248b71523f07feaa21e`.
Source imports the locally mounted E-D2 implementation for direction definitions, and is **not independently runnable from this docs-only GitHub note**. Original code/raw bytes are not in the FORGE repo. Remote authenticated custody and scientific promotion remain UNVERIFIED.

## Decision and next gate

**No transfer claim.** E-D4 should test *stateful causal adaptation* in the unseen two-barrier family, separating an agent that can carry forward a learned construction strategy from a conventional model-based explorer with equal observability and opportunity; include zero-shot and bounded adaptation curves, construction-cost accounting, state resets and strong trained baselines. Require independently qualified original source/holdout custody before any first-use claim.

**Plain English:** The simpler visual representation helped the learner get through one wall, but it could not reuse that skill when the world required breaking through two walls. The manually written builder still solved both.
