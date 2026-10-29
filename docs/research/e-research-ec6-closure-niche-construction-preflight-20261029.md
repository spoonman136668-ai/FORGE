# E Research E-C6 — closure audit and niche-construction experiment preflight

**Date:** 2026-10-29  
**Gate:** E-C6 — protocol/design only, **no new experiment executed**.  
**Authority:** Advisory draft in FORGE PR #1194. No scientific first-use, FSA acceptance, native model selection, owner/controller/queue change, or deployment.

## Source check and narrow closure

Verified existing branch record `docs/research/e-research-ec5-extinction-scored-fit-20261029.md` before writing this follow-on. Its 30 FIT evaluations (six development seeds × five arms) found median 300-opportunity harvested-resource rates: evolving/dynamic **0.008325**, evolving/static **0.005112**, random-parent **0.001783**, greedy reactive **0.0404**, reduced 3-candidate policy search **0.0042**. Those are *descriptive FIT medians*, not independent qualified scientific evidence. Training organism-steps were not matched and original executable/result bytes are not held in FORGE. Thus:

- **Close:** Claim that this specific E-C1–E-C5 resource-harvesting ecology demonstrates emergent intelligence or evolution beating a competent reactive control: **NOT SUPPORTED**.
- **Do not claim:** General failure of evolving agents, ecological evolution, open-ended novelty, or transferable native cognition.
- **Preserve:** Resource-ledger checks, extinction-as-outcome scoring, baseline dominance, and provenance limitations. Do not retrofit a better score after viewing results.
- **Stop:** Further parameter tuning of this exact ecology as a route to a positive science claim.

## E-C7 prospective scientific idea: local niche construction

**Hypothesis (testable):** Organisms with a *locally enacted, costed environmental modification* can cause the future ecological opportunities their descendants experience to improve in unfamiliar world layouts, beyond a no-construction population, a static policy, random construction, and resource-equal reactive controls.

**Mechanistic difference from E-C1–C5:** Earlier organisms only harvested or moved through an externally supplied resource schedule. Here the organism can **alter a persistent local environmental state**. These alterations must have explicit physical/material costs and can help, hurt, or decay. Individual action-conditioned construction and intergenerational inheritance are separated analytically: environmental persistence alone is not within-lifetime cognitive memory.

### Candidate environment, prior to implementation

- 20×20 toroidal grid with nutrient quantity `n[x,y]`, habitat permeability `h[x,y]`, construction-material budget `m[x,y]` and a small fixed-cap population. Observations remain local (current tile + four neighbors). Never expose future weather/seed/fitness directly.
- Actions: move, harvest, wait, construct. Construct consumes a declared amount of energy and local construction material to increase local permeability/retention; identical abiotic decay applies to all arms. Harvest converts local nutrient to organism energy. Birth partitions parental energy and genome and never creates resources.
- Weather episodes: independently seeded disturbance regimes that can move available nutrients between impermeable and permeable regions; a construction action must not simply reveal answer labels or provide free food. Frozen FIT disturbances and rotated/relocated validation families, distinct from withheld first-use holdout.
- Track conservation where physically applicable, with an explicit ledger for sunlight/external replenishment, organism metabolism, construction-energy expense, nutrient uptake, weather flux, chemical decay and diffusion. If the habitat parameter is informational rather than conserved matter, report its update budget separately; do not call it mass-conserving.
- No privileged coordination or global optimizer. No genome-to-world direct writes besides declared local actions. Same observation, simulation seeds and public environmental schedule per matched episode.

### Six arms, with exact causal ablations

1. **Evolved construction:** mutation/selection of local policy that can construct, harvest, move.
2. **Evolved no-construction:** same policy parameterization and search budget, construction action replaced by zero-benefit wait at same energy cost; state/action capacity disclosed.
3. **Random construction:** same construction opportunity and costs, locations selected independently of sensed conditions.
4. **Reactive construction heuristic:** same local observations and resource budgets, explicitly coded conventional baseline.
5. **Static-evolved construction:** optimize same policy under static environmental regime, test under common changing ecology.
6. **Ablated environmental persistence:** allow paid construction but reset altered habitat every step; isolates persistent environmental inheritance.

Where these arms differ in possible intervention opportunities, match potential decision slots, account actual organism-action and parent-selection budgets separately, and score extinction as zero subsequent opportunity reward. Also require a greedy/no-construction harvesting baseline from E-C5 recalibrated on the new world before scientific comparisons.

### Prospective metrics and decision

**Primary FIT measure:** nutrient harvested per 300 potential organism-decision opportunities in a matched unfamiliar resource layout, including zero harvest after extinction, minus the strongest conventional control. Record confidence intervals and per-seed differences, not solely medians.

**Causal niche-construction assay:** matched pre/post-exposure environmental state and subsequent harvesting opportunities, including `h` reset as an ablation. A positive result must survive random construction, matched energy/material expenditure and differential survival controls.

**Secondary:** birth count, lineage survival after weather regime change, ecological persistence after constructor death, resource transfers, peak memory, wall/CPU, environmental/lineage novelty. Novelty alone is not cognition.

**Falsification:** If any apparent improvement disappears after matching costs, construction count/placement, environmental persistence or conventional reactive strategy, report no supported niche-construction advantage. If only population evolution across episodes improves, report evolutionary adaptation and explicitly **not** individual learning.

## Execution readiness and boundaries

**E-C6 design PASS. E-C7 experiment NOT RUN.** Before any FIT run: freeze parameter table, physical step updates, action observation interface, deterministic replay harness, budgets, validity invariants, seed list, baseline resource parity and failure preservation. Frozen independent validation/held-out identities, source-birth custody and first-use scientific approvals remain distinct gates. Stop at scientific authority boundary; do not present a protocol as executed science.

**Plain English:** The existing evolutionary world was too easy for a greedy agent. The next independent test asks whether organisms can make costly, durable improvements to their habitat that help future organisms. If so, we must prove the benefit comes from what they built—not from more food, more training or a hidden shortcut.
