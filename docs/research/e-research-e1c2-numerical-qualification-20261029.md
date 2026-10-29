# E Research E1-C2 — numerical failure diagnostic and controlled rerun (2026-10-29)

**Status:** FIT engineering validity PASS on 36 seed/model groups × 4 trajectories = 144 trajectories; **scientific adaptive-repair/learning UNVERIFIED**. Advisory only, no FSA/first-use acceptance. This is isolated session work, not FORGE-run CI or its owner controller.

## Root cause localization
E1-C's sole observed invalid state was **fixed_random** seed **12003**, **localized_noise**, nominal step **501**, chemical **u**, grid position **(27,34)**, value **−0.005603519509479682**. Previous u at that cell was 0.6174869510750579. This is a one-step post-perturbation numerical undershoot of explicit Euler integration after a steep local gradient; the diagnostic alone cannot prove the mathematical source beyond that localized mechanism. The implementation did not clip evolving concentrations.

## Controlled numerical change
Preserved same grid, seeds, modes, disturbance locations/noise generator and 1000 units of simulated time, with damage at unit 500. Replaced each original Euler step of dt=1 with **two Euler substeps at dt=0.5**, without runtime concentration clipping or new adaptive/repair logic. Executed the same 12 FIT seeds in three modes and four paired trajectories: **144 trajectories**. All states met existing finite/nonnegative checks at nominal observation points, with zero reported invalid entries. Deterministic terminal hash replay on the first Gray–Scott seed PASS. **Caveat:** validity scanning is at the end of the two-substep nominal step, not each intermediate substep; this is engineering provisional, not exhaustive positivity proof. Independent CI on FORGE runners NOT RUN.

### Final median normalized disturbance error (lower relative difference, not proof of repair)

| condition | central erase | offset erase | localized noise |
|---|---:|---:|---:|
| Gray–Scott | 0.456062 | 1.447737 | 1.286846 |
| Diffusion | 0.447494 | 0.388892 | 0.164890 |
| Fixed-random | 0.740951 | 1.150198 | 0.620911 |

All four outcomes: spatial-pattern persistence remains observable; Gray–Scott's offset and noise errors exceed 1 and are worse than passive diffusion, so **functional self-maintenance is not demonstrated**. E1-C2's smaller timestep does not rescue that scientific hypothesis.

## Source and evidence identity
Session-original source/results SHA-256 digests, not Git commit provenance:
- `diagnose.py`: `511efbcbdfad4b6424405efd0b2a371557f3a3a266d8d4e2e5d573783a9a1a07`
- `diagnosis.json`: `8424a58b036295dc3cf1778aa9c4efc96bd64edac6cca8cdd4f9654f5ccd9101`
- `qualify.py`: `4ceafbb56fcdc6c055a22b117556fcf9117f8cf403695e66a42b7724dc27adf3`
- `results.json`: `25277f086db2c37d64f4fefd9e69f18e9c00047f4006ed9a022f805fd159102a`

Source scripts for both stages are committed adjacent to this advisory document for independent rerun, but **the raw JSON evidence remains session-local** pending repository evidence-storage policy qualification. Do not silently claim original-byte custody in GitHub.

## Next scientific gate

E1-C3: Test half-substep positivity explicitly, add numerical convergence comparisons at dt=0.25 and matched continuum physical time, and analyze structure vs relaxation. Preserve negative results; do not infer cognition or alter FORGE selectors/controllers. Later E2 memory tests require separate frozen protocol/held-out first-use clearance.
