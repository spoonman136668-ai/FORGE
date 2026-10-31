# E Research E2-M1 — explicit slow-memory mechanism control (2026-10-29)

**Status:** Isolated FIT engineering PASS, **spontaneous learning NOT demonstrated**, independent scientific qualification UNVERIFIED. Advisory only: no FORGE runtime, native controller, scientific first-use, model selection, owner/witness or acceptance changes.

## Question
Does adding a *deliberately engineered* local slow-memory field to the existing two-species Gray–Scott grid produce a cue-dependent history response distinguishable from ordinary residual chemical differences?

## Experiment actually executed
- 64×64 periodic Gray–Scott dynamics; same original six FIT seeds (12000–12005), four history events at t=40/70/100/130, probe at t=200, readout t=199 to 210, dt=0.25 in 4 substeps.
- Third field m at output locations. **Engineered memory:** every consequence presentation directly increments m at the corresponding port; m decays by factor (1−0.001×dt) each substep. **Engineered readout wiring:** only when probe cue is present, v reaction at both output regions receives +0.002×m. The cue flag is externally supplied globally. This is *not spontaneous emergence or learned routing*.
- 6 FIT seeds × 2 balanced outcome histories (ABAB/BABA) × 2 cue/sham probes × 2 memory-present/ablated = **48 trajectories**.
- Intermediate-step finite/nonnegative check PASS for all; seeded deterministic terminal replay PASS.
- Primary measured quantity: [(ABAB minus BABA response with cue) − (ABAB minus BABA response with sham)], where output is v(OUT)−v(OTHER), response is post minus pre.

| Condition | Median history contrast: cue | Median history contrast: sham | Cue-specific history interaction |
|---|---:|---:|---:|
| Engineered slow-memory field | −0.00009655005 | +0.00001808711 | median −0.000114637 (all six approximately equal) |
| Memory ablated | +0.00001808711 | +0.00001808711 | exactly **0** in all six seeds |

**Interpretation:** The measurement distinguishes *explicit designed state storage and hardwired cue gating* from an ablated variant. It does NOT demonstrate associative learning, local discovery of a causal relation, long-distance communication emerging without wiring, native cognition, useful transfer, or scientifically qualified advantage over an equally capacitated conventional associative lookup. This serves as a deliberately positive assay control, not a scientific positive E Research discovery.

## Evidence and custody

Isolated local original artifacts, not included in this GitHub commit:
- `/mnt/data/e_research/e2m1/run_e2m1.py` SHA-256 `cc4a2cae17549dc686a4aaac56de721981698088bc47c603c606171fce8fb443`
- `/mnt/data/e_research/e2m1/results.json` SHA-256 `cb5e9f3a220556e9e4b072ffe658fc9f49b776f9eac0d7ff9b907a5ce5c398b4`

These hashes are identity pointers, **not independently authenticated original-byte custody**. Reproduction from the repository alone UNVERIFIED. No validation or heldout scientific first-use, independent review, resource-matched baseline, independent washout certification, or cold-restart memory test was performed. Approximate local measured walltime: 4.30 seconds for this FIT pilot; not full CPU/RAM accounting.

## Next gate
**E2-M2:** remove the globally delivered cue gate and the direct teacher write into m; instead use exclusively local chemical transport, and compare against same-state-capacity hardwired and no-learning controls. Require a prospective predictor score and matched information/interaction resources; failures must remain visible. Keep a *separately labeled* engineered-memory positive assay as a control, not candidate emergent intelligence.

**Plain English:** Adding an explicitly programmed memory gives the system a history-specific response, as expected. The baseline does not produce it. We have checked the measuring apparatus but have not produced emergent learning.
