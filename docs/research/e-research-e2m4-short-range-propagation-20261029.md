# E Research E2-M4 — short-range propagation FIT execution (2026-10-29)

**Status:** Engineering PASS (24 FIT trajectories, checked every substep, deterministic terminal replay). **Associative learning NOT TESTED; memory benefit NOT SUPPORTED.** Advisory only; not FORGE-scientific acceptance, FSA custody, or any controller/model change.

## What executed

The E2-M3 reaction–diffusion impulse-response test was rerun for a source-defined shorter output region using six previously used FIT seeds, local chemical-memory field vs ablated control, matched cue vs sham. 64×64 periodic grid, stimulus at `slice(8,12),slice(8,12)`, v increment +0.04 and corresponding nonnegative u decrement; dt=.25, four substeps per unit, physical time through 120. No history training, memory-cue supervision, new model or HOLDOUT; 6 seeds × 2 modes × 2 cue conditions = **24 trajectories**. All intermediate states finite and nonnegative (threshold −1e-10): PASS. Seeded terminal replay: PASS.

Observation regions fixed before executing: adjacent (rows 8:12, cols 12:16), near (8:12,16:20), middle (8:12,24:28), distant original OUT (44:48,44:48). Report **maximum absolute difference** across six FIT seeds between matched cue and sham at the listed step; this is an exploratory deterministic magnitude, **not signal-to-noise qualification**, hypothesis test, prediction or confidence bound.

| Region | t=10 local | t=40 local | t=80 local | t=40 ablated |
|---|---:|---:|---:|---:|
| Adjacent | 0.001686536832 | 0.000141647940 | 0.000002578030 | 0.000141647578 |
| Near | 0.000002603697 | 0.000009421801 | 0.000000537257 | 0.000009421792 |
| Middle | 1.581e-15 | 4.602e-10 | 1.334e-9 | 4.602e-10 |
| Original far | 0 | 0 | 0 | 0 |

Memory-present and ablated are nearly identical: at adjacent t=40 the max-absolute signal difference is ~3.62e-10; near ~9.56e-12. The near region therefore permits an observable, deterministic physical cue perturbation, but there is **no supported advantage attributable to memory**.

## Exact local source/results digest pointers

- `/mnt/data/e_research/e2m4/run_e2m4.py` SHA-256: `0b7f2dd0ce517195f56b0148fab559a146c3019731091b408123b4afa9b08fae`
- `/mnt/data/e_research/e2m4/results.json` SHA-256: `a9a2f6c808f60525dd492102dea9e78206567ddbb6e6907a16acb0dd7bc67181`

The source imports the original session `e2p1/run_e2p1.py`, which itself imports E1-B physics. This document and its digest pointers alone do **not** durably preserve a complete independently executable source tree or raw results. No authenticated original birth, independent validation, sealed heldout, FSA receipt or FORGE-run CI happened. Elapsed local time 1.625s; no peak memory or CPU-time accounting.

## Next decision

**E2-M5:** Freeze an explicitly predeclared short-range paired-history cue-sham experiment with identical present input, balanced historical stimulus doses, and separate state-matching diagnostics. Include passive dynamics, ablated-memory and explicit finite-state-memory controls at matched observations/budgets; preserve cue/signal/noise measurements and a model-agnostic predictor score. If FIT remains no better than residual-state/passive controls, terminate this chemical-association subline rather than indefinite tuning.

**Plain English:** Moving the output closer lets us see the stimulus. Ordinary chemistry transmits it just as well as our added memory, so this does not show learning.
