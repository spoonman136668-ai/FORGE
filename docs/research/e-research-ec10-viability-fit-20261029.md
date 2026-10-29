# E Research E-C10 — ecological viability calibration (2026-10-29)

**Status:** Engineering PASS from isolated local FIT experiment; scientific learning, evolutionary niche construction and unfamiliar transfer UNVERIFIED. Documentation-only; no native FORGE runner/owner/controller/model-selection changes.

## Execution and constraints

270 trajectories = six development seeds 41000–41005 × three fixed sites (hotspot, ambient, shifted) × five resource supply/metabolism settings × three interventions (no construction, equal-cost sham, persistent construction). Each trajectory is 300 steps; local world is the E-C9 single-site fixed-harvest ecological model with environmental resource renewal and energy-split reproduction at threshold 1.6 with at most two agents. Construction costs 0.08 energy and 0.12 material and creates habitat increment 0.22 with 0.998 decay and +0.7*h renewal multiplier.

This is a **parameter-screening viability calibration**, not a policy-learning experiment. It tests alternatives at FIT only and must not serve as fresh independent validation. A permanent benefit of construction is programmed into habitat-renewal physics; it is not emergent intelligence.

| Supply / metabolism | No-construction fraction with >=1 birth | Cost-sham fraction | Persistent construction fraction | No-construction survival at t300 | Construction survival |
|---|---:|---:|---:|---:|---:|
| 0.002 / 0.025 | 0/18 | 0/18 | 0/18 | 0/18 | 0/18 |
| 0.008 / 0.025 | 0/18 | 0/18 | 0/18 | 0/18 | 0/18 |
| 0.018 / 0.025 | 2/18 | 2/18 | 8/18 | 11/18 | 16/18 |
| 0.008 / 0.012 | 9/18 | 4/18 | 13/18 | 17/18 | 18/18 |
| 0.018 / 0.012 | 18/18 | 18/18 | 18/18 | 18/18 | 18/18 |

No-construction is viable under lower metabolism with higher resource supply. This meets the **engineering precondition** of occasional offspring and sustained survival without first programming a beneficial construction action into the agent's policy. It does *not* show an intergenerational causal advantage: fixed site, a maximum of two co-located agents, no evolving policies, no competition, no independent controls for spatial inheritance, and no unfamiliar transfer. The stronger construction variant can perform better because habitat improves renewal by explicit physics.

**Engineering:** maximum ledger residual 1.078026556911027e-13; all energy/nutrient/habitat/material bounds checked per step; exact first-trajectory replay PASS. Experiment wall ~0.48 seconds on current session. No full CPU or peak RAM accounting and no independent FORGE CI.

**Original local source:** `/mnt/data/e_research/ec10/run_ec10.py` SHA-256 `441f3535420967ccdd1b5dc9a33f9ae2e52cc3c25816803a7978b3d10122b3fc`.

**Original local JSON:** `/mnt/data/e_research/ec10/results.json` SHA-256 `d06ff61785795e12d364b00d8ff098a2db86a765e0535c363b04a5b191d41bd8`.

Original bytes are local session evidence, **not in this docs-only FORGE commit**, not independently preserved under FORGE FSA and not sufficient for repository-only reproduction. No scientific first-use, holdout, independent witness or acceptance claimed.

## Decision

E-C10 **viability calibration PASS**. Freeze candidate test configurations prospectively for E-C11; do not tune on or claim first-use from FIT. Next experiment must include physically spatial environment inheritance, nonbuilder controls, fixed reactive constructors, matched paid sham, habitat reset and progeny benefit measurement. Maintain actual organism-action budgets and energy/material ledger. If effect is only the explicitly programmed habitat benefit, label it **ecological engineering**, not intelligence.

**Plain English:** Lower energy costs or higher resource supply permit the organisms to survive long enough to have offspring. That makes a real descendant test possible later, but it does not make the organisms intelligent.
