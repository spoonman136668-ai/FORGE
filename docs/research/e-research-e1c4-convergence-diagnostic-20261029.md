# E Research E1-C4 — fixed-random convergence anomaly (2026-10-29)

**Classification:** Executed FIT numerical diagnostic; scientific self-maintenance and learning **UNVERIFIED**; **advisory only**. Existing FORGE runtime/controller, native models and first-use records unchanged.

## Scope

Investigated E1-C3's outlying first-order convergence ratio **0.412762** for the fixed-random-reaction control, FIT seed **12004**, on an **unperturbed trajectory**. Reused the existing 64×64 initial state, spatially fixed local feed/kill parameters, same RNG seed offsets, periodic Laplacian, physical duration 1000, and explicit Euler integrator. No new learning, adaptation, damage, clipping or model selection. Four original FIT seeds (12001–12004) at substeps 1, 2, 4, **8** (Δt=1, 0.5, 0.25, 0.125); **16 unperturbed trajectories** in this diagnostic. An earlier E1-C3 script already measured substeps 1, 2, 4; this is a focused replication plus finer-resolution observation, not an independent holdout.

## Exact unperturbed terminal-v RMSE between successive timestep resolutions

| FIT seed | RMSE Δt 1 vs .5 | RMSE .5 vs .25 | RMSE .25 vs .125 | error ratio (1/.5)/(.5/.25) | ratio (.5/.25)/(.25/.125) |
|---|---:|---:|---:|---:|---:|
| 12001 | 0.005758005 | 0.002560873 | 0.001267582 | 2.24845 | 2.02028 |
| 12002 | 0.002174007 | 0.001098220 | 0.000551478 | 1.97957 | 1.99141 |
| 12003 | 0.002119334 | 0.001073719 | 0.000541385 | 1.97383 | 1.98328 |
| **12004** | **0.025611603** | **0.062049290** | **0.020926103** | **0.41276** | **2.96516** |

**Finding:** Three seeds exhibit near-first-order successive error reduction at finer Δt. Seed 12004 does not: reducing Δt from .5 to .25 produces a larger terminal discrepancy, then Δt .125 reduces it but not at a stable factor. The anomalous ratio is not an arithmetic mistake; it repeats in a focused source-derived diagnostic.

**Interpretation:** Reproducible **nonuniform numerical convergence / sensitivity** under this spatially heterogeneous reaction model. A precise dynamical explanation (e.g. phase shift, attractor switching, bifurcation) **has NOT been established**. Terminal finite-time RMSE is insufficient to assert eventual convergence of structures, and no evidence for adaptive repair, memory or intelligence follows. Do not conflate timestep sensitivity with emergent cognition.

## Evidence/custody
- Session probe script: `e1c3/e1c4_probe.py`; local SHA-256 `0f2fe0490ecf8fded0b72826a0b1daeb008249e194aff5838ac79d374e0465c9`
- Session JSON: `e1c3/e1c4_probe_results.json`; local SHA-256 `b1f776eb31e0303abb4c421893d33c5bf47f4999bafc121eefe715ad27e337b2`
- **Neither source nor raw JSON is stored by this documentation-only GitHub commit.** Digest values are not authenticated original-byte custody. Independent FORGE-run reproduction and scientific first-use UNVERIFIED. No frozen held-out population was opened.

## E1 decision

**Close the hypothesis that these tests demonstrate adaptive self-maintenance: NOT SUPPORTED.** Do not close the broader possibility of emergent memory/learning in other systems, which was not tested. Preserve negative evidence and nonuniform convergence warning.

**Next eligible gate E2-preflight:** Define prospective history-dependent intervention and reset controls, deterministic physically valid challenge, matched explicit-memory and passive-dynamics baselines, and separate FIT/VAL/HOLDOUT; do not run first-use/heldout without authorization and source-birth controls. Do not inject unqualified findings into FORGE selection.

**Plain English:** Three cases behave predictably when the computer uses smaller timesteps. A fourth can end up in quite different spatial states despite finer numerical precision. That is a warning about the simulation, not evidence of an intelligent chemical organism.
