# E Research E-C13 — feeding-order control and offspring attribution (2026-10-29)

**Status:** Isolated FIT experiment executed; engineering PASS; evidence for genuinely evolved niche construction **UNVERIFIED**. Research advisory only; no FORGE owner, runtime, FSA acceptance, scientific first-use or model selection mutation.

## Source and design

Derived E-C13 from the actual session-mounted E-C12 source (`run_ec12.py`) with *only* the order of agent harvesting changed across three predeclared conditions. The same fixed-site resource-renewal equation and habitat persistence/reset, energy-split reproduction, and construction costs remain. Three schedules: parent first, offspring first after birth, and alternating priority by timestep. For each schedule and each environment, matched arms are persistent habitat, reset-at-first-birth and cost-matched no-habitat sham.

Six existing FIT seeds × three existing sites × three viability configurations × three schedules × three arms = **486 trajectories** at 300 simulation steps. No genomes, evolving behavior, new scientific holdout, or independent validation. Fixed single-site food access is a highly simplified model of inheritance.

## Numerical results and original-record correction

Every-step finite/nonnegative and ledger assertions PASS; max absolute mass-energy accounting discrepancy **1.1812772982011666e-13**. First trajectory deterministic replay PASS. Physical habitat alteration and environmental nutrient renewal are explicitly programmed, not emergent.

For supply 0.018, metabolism 0.012 (18/18 FIT pairs born in each schedule), median **extra harvest after birth**, persistent minus habitat-reset:

| Harvesting schedule | Parent | Offspring | Offspring positive pairs |
|---|---:|---:|---:|
| Parent first | +0.6638378517 | 0 | 0/18 |
| Offspring first | 0 | +0.6638378517 | 18/18 |
| Alternating | +0.3322511770 | +0.3315866747 | 18/18 |

At supply 0.008, metabolism 0.012: 13/18 birth pairs; median offspring benefit among born pairs is 0, +0.3276460857, +0.0930371390 for parent-first, offspring-first and alternating respectively. At supply 0.018, metabolism 0.025: 8/18 birth pairs; corresponding offspring benefit 0, +2.0398244353, +0.1041559240. These are conditional descriptive FIT medians; no confidence intervals or population inference.

**Correction of earlier interpretation:** E-C12's result of zero offspring gain was dependent on a **hardcoded parent-first harvesting order**. This does not support a general claim that offspring cannot benefit from inherited habitat. Switching priority transfers the *programmed physical resource gain* to the offspring; alternate feeding shares it. This is an **allocation-effect diagnostic**, not an evolutionary or learning discovery.

## Original-byte provenance (not yet remotely deposited)

- Session source `/mnt/data/e_research/ec13/run_ec13.py`, SHA-256 `ab331d85692bbfc0950f341f71670c15aa8eca0265ffa61b9a5c7671e8a0b0f5`.
- Session original JSON `/mnt/data/e_research/ec13/results.json`, SHA-256 `26a25fce00f708b6110e2498a8ddecf7f2096272bc0834b4621d584b02420246`.
- E-C13 imports the session-local E-C11 module for seeds, site choices and configurations. Original executable and machine-readable results have **not** been placed in this documentation-only GitHub commit. This advisory report alone cannot independently reproduce or authenticate the FIT finding; no FORGE CI or FSA scientific first-use clearance.

## Decision and next gate

**E-C13 engineering PASS / learned environmental inheritance UNVERIFIED.** Avoid inferring descendants gain from niche construction in realistic ecologies merely from harvest priority in a shared reservoir. **E-C14** should introduce two spatially separable feeding sites with identical public observation and costs, and compare persistence/reset under randomized parent/offspring positions and feeding opportunity, alongside a conventional fixed constructor and nonconstructor. Do not repeat the current single-site test as if it were independent. Require separate daughter/parent energy and survival measures and resource parity.

**Plain English:** The previous child's zero benefit was caused by the parent always eating first. Giving the child a chance to eat lets it receive the extra resources. We have verified the confound, not intelligence.
