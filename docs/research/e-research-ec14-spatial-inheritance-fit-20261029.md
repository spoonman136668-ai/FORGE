# E Research E-C14 — two-site offspring inheritance FIT (2026-10-29)

**Engineering PASS** in isolated local numerical experiment. **Scientific emergent learning / evolved construction UNVERIFIED.** Advisory only, no FORGE-native first-use, runtime, controller, model promotion, or accepted science.

**Experimental source:** 20×20 abstract ecology reduced to two separately replenished resource sites. Habitat construction at site 0 is programmed (0.08 energy, 0.12 material), persistent with decay 0.998 and renewal multiplier 1+0.7h. A child receives half the parental energy and is seeded either at site 0 or at independent resource site 1. Parent and child cannot move in this diagnostic. Parent-first, offspring-first, or alternating harvest priority. Paired arms: persistent habitat, habitat reset at first birth, and construction-cost-matched sham. No learning or evolution; this is an isolated causal control.

**Execution:** 6 reused FIT seeds (41000–41005) × 2 supply/metabolism configurations (.008/.012, .018/.012) × 3 feeding orders × 3 interventions × 3 site-placement environment replicates = **324 trajectories**, each 300 steps. Numerical range and conservation assertions PASS; max ledger residual **2.8066438062523957e-13**; first trajectory deterministic replay PASS. Different site placement is independently seeded by seed/replicate, not a held-out transfer cohort. FIT-only, no inferential claim.

**Primary descriptive result, high-viability setting .018/.012:** nine birth-capable matched pairs per child-location/feeding-order stratum, with median extra offspring harvesting from persistent versus reset habitat:

| Feeding order | Child site 0 (constructed) | Child site 1 (unmodified) |
|---|---:|---:|
| Parent first | 0 | 0 |
| Offspring first | 0.61247752 | 0 |
| Alternating | 0.30723091 | 0 |

Parent retains the benefit when child feeds at the unmodified site. At .008/.012 only one of nine pairs per stratum experiences a birth; inferential claims at that supply are particularly unsupported.

**Interpretation:** Additional harvested resource follows direct local access and priority. Nothing demonstrates that an organism learned to construct, that a new behavior evolved, or that inherited capability transfers to unfamiliar environments. Two-site separation is a deliberately simple diagnostic; the habitat-boosting chemistry is preprogrammed.

**Original isolated artifacts (not committed in this report):**
- `/mnt/data/e_research/ec14/run_ec14.py`, SHA-256 `5957f2878b7dd07e03ee2e4c335e9723753952c7003388e8fc3652fd6a3923da`
- `/mnt/data/e_research/ec14/results.json`, SHA-256 `75d0e6a72dcd6f1ea00c205c1aeb383a4d983a426713b97427b1cbb8bd0f95ec`

The local source and raw results are **not** under independently authenticated FORGE FSA custody and cannot be reproduced solely from this documentation branch. No FORGE CI, frozen validation or scientific first-use.

**Next gate E-C15:** Determine whether *behavioral* niche construction evolves when habitat modifications are costly but potentially improve descendant-relevant conditions. Test evolved versus random/fixed/reactive constructors with equal decision opportunities, resource costs and training search budgets, under a spatially meaningful environment rather than tuning the two-site programmed-affordance assay. Keep E-C14 as a physical baseline, not a cognition discovery.

**Plain English:** Children only benefit from the shelter's food when they actually occupy it and get a chance to eat. No intelligence or learning has been demonstrated.
