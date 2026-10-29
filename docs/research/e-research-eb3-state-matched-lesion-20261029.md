# E Research E-B3 — state-matched repeated-lesion control (2026-10-29)

**Status:** Locally executed FIT numerical PASS, but adaptive-repair learning **NOT SUPPORTED**. This is advisory-only; not FORGE native FSA custody, scientific first-use, model selection, acceptance, or runtime change.

## Experiment and controls

Reused exact E-B1 fixed update physics and E-B2 lesion definitions: 64×64 two-field mass-conserving lattice, 8 FIT seeds 22000–22007, 3 conditions (programmed active biomass conversion, passive diffusion, frozen), 3 lesion regions (center8, offset8, center12). Preconditioning 250 steps, first lesion and 200-step recovery, second lesion and 200-step recovery. 72 case groups; each compares a previously lesioned history to a same-aged no-lesion history.

Two new comparisons:
1. **Complete-state matching:** Clone the same experienced full (b,n) state into both second-episode histories, then apply the same lesion and 200 steps. Terminal error is **exactly zero in all 72 groups**. This is a deterministic control, *not* a proof that history cannot matter through internal states in a different architecture.
2. **Matched total removed biomass:** For the experienced and naive arms independently remove the same total biomass (minimum of their available lesion-region biomass), transfer to nutrient, and run 200 steps. This matches integral dose, **not the spatial damage field or entire pre-challenge state**. Separate immediate damage RMSE denominators and whole-grid reference twins are used in normalized-error estimates.

All final finite/nonnegative states and total mass to <1e−6 PASS. Exact replay of first active center8 seed PASS. No separate preprogrammed adaptive-repair controller was implemented: earlier active-growth control is *already* programmed and immutable. No novel adaptation mechanism, heldout or new coefficient optimization.

### Median second-lesion normalized whole-grid error (8 FIT seeds; lower means closer to own undamaged reference)

| Mode | Lesion | Experienced | Naive | Prechallenge experienced-vs-naive state RMSE |
|---|---|---:|---:|---:|
| Active fixed-rule | center8 | 0.577109 | **0.25377** | 0.07181 |
| Active fixed-rule | offset8 | 0.698154 | **0.22997** | 0.08599 |
| Active fixed-rule | center12 | 0.716230 | **0.19843** | 0.12385 |
| Passive diffusion | center8 | **0.615781** | 0.83530 | 0.01561 |
| Passive diffusion | offset8 | **0.601884** | 0.81301 | 0.01105 |
| Passive diffusion | center12 | **0.61391** | 0.88970 | 0.02500 |
| Frozen | all | 0 | 0 | nonzero |

Note: Frozen-model zero is trivial because the damaged and own reference trajectories both remain fixed after damage; zero deviation is **not functional repair**. The experienced state is already different before the second lesion. The matched-total-biomass perturbations differ spatially, so relative errors are descriptive and cannot isolate learning effects.

**Decision:** E-B1–E-B3 provide no credible evidence that this fixed-rule lattice learned adaptive self-repair. Stop the tested fixed-rule learning subline rather than tuning indefinitely. This is not a universal rejection of developmental artificial-life self-maintenance.

## Original source and raw evidence

- `/mnt/data/e_research/eb3/run_eb3.py` SHA-256 `66139dc419d42960a1b3a4e8ae5cbe22f6b4912fa16744df9c8f6143cd05e37c`
- `/mnt/data/e_research/eb3/results.json` SHA-256 `490d41c9f0a5a6d40e9852a11c87dc8d72ac26619dadd8371715f14f89171c3f`
- Source depends on local `eb1/run_eb1.py` and `eb2/run_eb2.py`. These files and results **are not committed by this documentation-only report**. SHA-256 pointers alone are not independent source custody.
- 72 FIT case groups ran in ~8.08 s session wall time; no complete CPU/RAM resource accounting, FORGE CI, independently authenticated original first-use, or held-out transfer.

## Next authorized research step

E-C0: freeze a minimal **ecological novelty** world and objective controls on FIT only, checking diversity against stochastic novelty, fixed-environment evolution, randomized ecology and resource-matched conventional policies. No claims of open-ended intelligence until measurable acquired and unfamiliar-transfer capabilities. Preserve native independent FORGE/Wingless/Yggdrasil workflows.

**Plain English:** Starting from the same complete state produces the same outcome. After a prior lesion, the active material does worse when the second damage is normalized against its own baseline. The earlier apparent improvement did not show learned repair.
