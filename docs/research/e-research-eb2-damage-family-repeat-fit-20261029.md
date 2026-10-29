# E Research E-B2 — heterogeneous damage and repeat-exposure FIT test

**2026-10-29 | Engineering PASS; experience-dependent learned repair NOT SUPPORTED; scientific acceptance UNVERIFIED.**

## Original experiment
An isolated CPU test reused the exact E-B1 64×64 mass-conserving lattice and unchanged fixed active-growth rule; passive diffusion and frozen controls. Eight original FIT seeds 22000–22007; 3 model conditions; three predeclared 8×8 center, 8×8 offset and 12×12 center lesion families. Damage converts biomass b to nutrient n while preserving mass. Precondition 250 steps; first lesion then 200-step recovery, followed by second matched lesion and 200-step recovery. Each exposed-history trajectory is compared with a same-aged no-first-lesion history, both challenged with an identical second lesion. **72 case groups** (8×3×3), each including the matched histories, not 72 independent held-out experiments. No mutation, selection, learning update or programmed repair introduced.

Deterministic exact replay PASS; finite/nonnegative and mass within 1e-6 checks PASS at final state. The E-B1 integration routine checks nonnegativity per substep. No independent FORGE CI.

## Per-family medians (8 FIT seeds)

| Control | Lesion | First-lesion local biomass ratio versus undamaged twin | Second-lesion normalized error with prior lesion | Without prior lesion | Experienced minus naive |
|---|---|---:|---:|---:|---:|
| Active fixed-rule | center8 | 0.420261 | 0.577109 | 0.659926 | -0.083082 |
| Active fixed-rule | offset8 | 0.361632 | 0.698154 | 0.729987 | -0.032029 |
| Active fixed-rule | center12 | 0.329199 | 0.716230 | 0.753277 | -0.037086 |
| Passive diffusion | center8 | 0.208313 | 0.615781 | 0.835297 | -0.219471 |
| Passive diffusion | offset8 | 0.188995 | 0.601884 | 0.813006 | -0.210897 |

**Critical interpretation:** The active fixed-rule material retains more local biomass after damage than passive diffusion for the examined families, but survival/regrowth is programmed. Repeat-damage normalized errors appear smaller after previous damage, **yet passive diffusion shows an equal or larger history-related improvement**. Different prior lesions alter the state and initial lesion amplitude; the normalized error cannot identify within-individual learning. These tests demonstrate **no adaptive repair learning**, and cannot support an organism/intelligence claim.

## Provenance

Original isolated source: `/mnt/data/e_research/eb2/run_eb2.py` — SHA-256 `de9579c33c7691892a76712723a5c95d7de94e9bcf0bc9989491ce73ec037086`.  
Original JSON: `/mnt/data/e_research/eb2/results.json` — SHA-256 `00b01fb5baa3e3cebc0ec6bbcb50d288714f7c393808f5bfd8fdbbedf5c77dbc`.  
Original summary: `/mnt/data/e_research/eb2/summary.txt` — SHA-256 `d22047fd3a3f1340049ef58da8063b7f5d53dd2574c2b97ce9b41e66eacda143`.

**Repository limitation:** Original bytes remain outside this FORGE branch; these digests do not establish independently authenticated original custody or reproducibility from the PR alone. No held-out use, scientific first-use, independent witness, accepted result, runtime/owner/controller/queue mutation or model training occurred.

## Decision and next eligible gate

Do not label this fixed-rule regrowth as emergent adaptive repair. **E-B3:** eliminate the state-difference confound using matched second-challenge *immediate damage amplitude*, same-state sham controls and a prospective functional-response criterion; include fixed programmed repair policy control. If state-matched effects cannot distinguish adaptation from passive relaxation, close this simple lattice's learning claim and move toward E-C ecological novelty, avoiding endless tuning. Preserve this negative evidence.

**Plain English:** The active material grows back because that is how we programmed it. Even lifeless diffusion appears to improve after a previous wound. Earlier damage changes the starting state; that does not show learning.
