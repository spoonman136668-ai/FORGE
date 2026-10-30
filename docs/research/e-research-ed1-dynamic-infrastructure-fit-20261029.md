# E Research E-D1 — isolated dynamic intervention FIT test (2026-10-29)

**Engineering PASS**, **learned construction UNVERIFIED**, advisory only. Not FORGE CI, native FSA custody, scientific first-use or controller/model mutation.

## Actually executed
Python standard-library 9×9 bounded grid, solid x=4 wall, start x=1 and goal x=7, 12 independent development seeds 51000–51011 varying start/goal y. Each agent has initial 110 energy, one construction material unit, 65 decision steps, harvest reward 8 only at destination; a local build removes one adjacent wall cell for energy cost 3 plus one material, no direct reward. Nonbuilding policies cannot cross. Four policies: random movement; greedy no-building; explicit **preprogrammed** builder; named `oracle_upper` that **uses the same heuristic as the builder** (not an independently computed optimal bound). Total **48 FIT trajectories**. Energy+spent = 110 and material+placed = 1 each step, no negative states. Reexecution of all 48 trajectories matched exactly (deterministic replay PASS).

| Policy | Reached goal | Total builds |
|---|---:|---:|
| Random | 0/12 | 0 |
| Greedy nonbuilder | 0/12 | 0 |
| Programmed builder | 12/12 | 12 |
| Same-heuristic reference (not an oracle) | 12/12 | 12 |

**Scientific conclusion:** A construction action can causally open a useful crossing and allow actual resource collection. The successful behavior is manually programmed. No reinforcement learner, evolved policy, within-lifetime adaptation, independent controls with local equivalent observations, or unfamiliar held-out transfer was tested. The reference control needs renaming/replacement by an independently calculated BFS planner upper bound.

**Validity caveat:** The simplified task contains one wall, one material unit and no weather or reproductive ecology; reward occurs only at goal. Builder can target known goal-relative y but may only act on an adjacent wall. The local observation contract is not yet formally enforced for every baseline; initial FIT engineering only.

## Original-byte custody
- Session script `/mnt/data/e_research/ed1/run_ed1.py` SHA256 `42bb988d91dccafe83f970a53717deb7493f71534bf0af57b2f6ce867a64d6a1`.
- Session results `/mnt/data/e_research/ed1/results.json` SHA256 `5d5bb98b80e829d9cdc6e5682bed1f9d28e96639b62482d7f86532873633dd2a`.
- These bytes are **not included** in this documentation-only report. SHA identifiers are lookup candidates, not remote custody, nor proof of independent FORGE qualification.

**Next gate E-D2:** Enforce identical local observations and legal-action masks for all policies, add impossible intervention and varied barrier layouts, replace duplicate `oracle_upper` with true evaluation-only shortest-path/BFS bound, and then execute bounded FIT adaptation with a simple learnable local policy and strong conventional controls. No claim of emergent intelligence without genuine held-out/source-birth clearance.

**Plain English:** A prewritten building rule solves the wall problem. That proves the environment is meaningful, not that intelligence has emerged.
