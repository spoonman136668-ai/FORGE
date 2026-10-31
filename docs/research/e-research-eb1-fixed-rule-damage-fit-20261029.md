# E Research E-B1 — fixed-rule local organism damage test (2026-10-29)

**Status:** Isolated executed FIT engineering PASS, scientific adaptive repair **NOT DEMONSTRATED**, advisory only. No FORGE-native first-use, model-selection, qualification or runtime change.

## Experiment
Executed local Python/numpy 64×64 resource-conserving two-field lattice model, 8 FIT seeds 22000–22007. Starting biomass b in center square and nutrient n=1−b. 250 steps initial, then an 8×8 central lesion transferring b into n (mass-conserving) and 200 more steps; compare each lesion outcome with its paired unlesioned trajectory. dt=.15, periodic boundaries.

Three independent conditions:
- **Active fixed-rule:** b grows according to hardcoded 0.12*b*n conversion, loses 0.015*b to nutrient, and both fields diffuse. No mutable policy, no local plasticity, no adaptation rule learned.
- **Passive:** identical initial fields, b and n only diffuse.
- **Frozen:** identical initial fields, no update.

**24 simulations** (3 controls × 8 seeds). Intermediate finite/nonnegative validity enforced by code, total b+n mass conserved within 1e−6. First-seed active deterministic replay passed.

| Condition | Median damaged/undamaged final b in 8×8 lesion region | Median final lesion-to-twin whole-grid RMSE / immediate lesion RMSE | Undamaged final biomass variance |
|---|---:|---:|---:|
| Active fixed-rule | **0.420261** | **0.718022** | 0.154157 |
| Passive | 0.208313 | 0.835581 | 0.00219448 |
| Frozen | 0 | 1 | 0.00275233 |

**Interpretation:** The programmed conversion mechanism causes more repopulation of the damaged region than diffusion alone, but even it ends at ~42% of its own undamaged reference biomass in that region. This is ordinary fixed-rule regrowth, not learned or adaptive repair. The two fields are mass-conserving by model construction; calling this spontaneous organism emergence would be incorrect. Median summaries alone do not establish statistical superiority or functional recovery. Damage at fixed center and small reused FIT seeds are not unfamiliar generalization.

## Original local evidence
- `/mnt/data/e_research/eb1/run_eb1.py` SHA-256 `b864ee31a38690f63a3ee4f7e237f575b8516d3dd49253fdd9b9b8f2c7a31bc3`
- `/mnt/data/e_research/eb1/results.json` SHA-256 `bf8c71259ea6d5f41fb5d868473798d686b9d8c12fe185c9fe7e2e61c54b8da3`
- Local measured elapsed time 0.962 s (does not include full scientific CPU/RAM accounting).
- These source and raw result bytes **are not included in this advisory GitHub commit**. Hashes alone cannot establish independent source custody. Repo-only reproduction UNVERIFIED, CI UNVERIFIED, held-out and independent scientific validation UNVERIFIED.

## E-B2 next gate
Use preregistered lesion-position/size families and fixed energy/resource budgets; compare fixed-rule regenerative model, passive diffusion, preprogrammed repair controller and randomized local update controls. Focus on whether recovery changes with *experience* after repeated perturbations and survives internal-state controls. Preserve negative results and do not infer learning from fixed-rule regrowth.

**Plain English:** The simulated material partially grows back because its rules explicitly tell it how to grow. That is useful as a benchmark, but not self-discovered repair.
