# E Research E1-C3 — numerical convergence, FIT-only (2026-10-29)

**Status:** Isolated executed numerical observation, **engineering PASS for Δt = 0.5 and 0.25** on checked states, **scientific learning/repair UNVERIFIED**. This is not a FORGE owner-run experiment, independent scientific first-use, verified FORGE-native FSA archive, or selection authorization.

## Design and execution
- Original 64×64 two-species Gray–Scott, passive diffusion and spatially fixed-random-reaction controls; 4 retained **FIT/development** seeds from the original 12; four paired trajectories per seed/mode (none, central erasure, offset erasure, localized noise).
- Physical time fixed at t=1000, damage at t=500. Euler substeps per nominal time unit: 1 (Δt=1), 2 (Δt=.5), and 4 (Δt=.25). No evolving-state clipping, new repair logic, training or held-out data.
- 3 modes × 4 FIT seeds × 3 timesteps = **36 groups, 144 trajectories**.
- Replayed seed 12000 Gray–Scott Δt=.25 terminal v hash: PASS.

## Numerical outcome

| Check | Δt=1 | Δt=.5 | Δt=.25 |
|---|---|---|---|
| Groups with at least one intermediate negative or nonfinite state | **1** | **0** | **0** |
| Minimum u, all modes/trajectories | −0.005603519509479682 | 0.09957050146891651 | 0.04973970816118957 |
| Minimum v | 0 | 0 | 0 |

**Reproduced failure:** Fixed-random seed 12003 localized-noise trajectory at t=501, chemical u. Smaller timesteps eliminate this observed violation for the four tested FIT seeds. These observations are not proof of nonnegative solutions for all possible parameters/initial states.

**Unperturbed final-v convergence errors** (median per-seed RMSE):
- Gray–Scott: Δt 1 vs .5 = 0.000929588; Δt .5 vs .25 = 0.000465104. Ratios near 2 for all four seeds (first-order convergence).
- Diffusion: 0.00000307909 vs 0.00000153971; ratios near 2.
- Fixed-random: 0.00396601 vs 0.00182955; per-seed error ratios 2.248, 1.980, 1.974, **0.413**. Convergence is not uniformly regular and needs characterization.

**Final normalized damage error at Δt=.25 (median, four FIT seeds; lower is closer to undamaged twin):**

| Mode | Central erase | Offset erase | Local noise |
|---|---:|---:|---:|
| Gray–Scott | 0.4433 | **1.4470** | **1.4781** |
| Passive diffusion | 0.4475 | 0.3884 | 0.1705 |
| Fixed-random | 0.8221 | 1.2594 | 0.5307 |

These numbers differ from the earlier 12-seed summary because this is a **4-seed convergence subset**; do not present them as the same population estimate. The off-center/noise results **do not support** adaptive repair. Higher mask overlap is insufficient to infer functionality.

## Custody, limitations and decision
- Original script and raw result JSON are generated in an isolated session at `/mnt/data/e_research/e1c3/`; they are **not committed to FORGE** and may not be persistently retrievable by native FORGE. Reproduction from repo alone UNVERIFIED.
- Outcome is **advisory evidence only**. No original source-birth, independent witness, held-out sealed validation, FSA acceptance, trainer integration or controller change.
- Do not interpret apparent chemical organization as memory/learning or dispatch an autonomous native model change.
- **Next:** inspect anomalous fixed-random per-seed timestep behavior with independent numerical tolerance and stability checks; then a distinct frozen experience-dependent E2 challenge would be needed for cognition claims.

**Plain English:** Smaller time steps stop an observed numerical glitch. They do not make the chemical patterns intelligent. Passive diffusion often comes back closer to the undamaged reference than Gray–Scott.
