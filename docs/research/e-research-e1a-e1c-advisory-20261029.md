# E Research E1-A–E1-C — advisory chemical-dynamics results (2026-10-29)

**Record ID:** E-RESEARCH-E1-20261029-FIT-ADVISORY  
**Status:** Advisory-only; **engineering FAIL** at E1-C; **scientific learning/self-maintenance UNVERIFIED**.  
**Origin:** Isolated ChatGPT-session CPU simulations, not a FORGE scientific experiment, native FSA original, independent witness, or sealed first-use event. This document preserves reported observations and source digests, **not authenticated original custody**. No promotion, dispatch, owner/runtime/controller change, or acceptance is implied.

## Purpose and relevance

Investigate whether minimal local reaction–diffusion dynamics can sustain organization and recover after disturbances before testing experience-dependent chemical memory. E Research is independent of Wingless, Yggdrasil and N Research. Do **not** infer training improvement or causal cognition from pattern formation.

## Actual experiments (FIT development only)

- **E1-A:** 64×64 two-species Gray–Scott periodic-grid dynamics versus diffusion-only and fixed-random-reaction controls; 12 initial seeds, 300 and 1,200 steps. Deterministic replay and numerical smoke checks reported PASS; initial diffusion baseline had negative initialization values and required correction. At 1,200 steps, median final V spatial variance: Gray–Scott 0.014798; diffusion 0.0000496; fixed-random 0.013022. Both Gray–Scott and fixed-random maintain spatial structure, so variance is not evidence of intelligence.
- **E1-B:** Corrected initialization, 12 seeds × 3 conditions × paired disturbed/undisturbed runs = 108 trajectories, 1,200 steps; central 16×16 erasure at step 600. Nonnegative states and replay reported PASS. Median normalized final perturbation error: Gray–Scott 0.332; diffusion 0.416; fixed-random 0.657. Passive diffusion also relaxes; this comparison does not establish repair.
- **E1-C:** 12 seeds × 3 conditions × 4 trajectories = 144 trajectories, 1,000 steps, disturbances at step 500 (central erase, offset erase, localized noise). Gray–Scott median normalized final error: central 0.4729, offset 1.4487, noise 1.3011. Corresponding active-mask Jaccard: 0.9895, 0.9147, 0.9744. High mask overlap does not establish functional recovery. **One invalid-state step** occurred in fixed-random seed 12003; exact trajectory, coordinate and step remain undiagnosed. Full physical-numerical qualification FAIL.
- All 12 seeds are development/FIT. **No validation/test holdout, independent scientific review, model training, learning, cold-restart retention, unfamiliar transfer, or first-use qualification.** The experiment does not demonstrate adaptation, memory or cognition.

## Negative findings and decision consequence

1. Simple pattern persistence can be matched by a fixed-random control and cannot be equated with adaptive intelligence.
2. E1-B's apparent center-damage recovery does **not** generalize to offset erasure/noise in E1-C: those conditions exceed an error ratio of 1.
3. Diffusion-only improves disturbance error in some comparisons without learning.
4. A baseline numerical-validity failure blocks confident interpretation of E1-C comparisons.

**Recommended decision:** Keep E Research in isolated exploratory mode. Do not pass this result into FORGE's accepted science, native architecture modifications, optimizer selection, or unattended generation as a positive scientific result. Preserve the negative/invalid evidence.

## Next eligible scientific step

**E1-C2 diagnostic:** Locate the fixed-random invalid state exactly (trajectory, step, coordinate and magnitude), investigate positivity and stability without silently clipping evolving states, then rerun the same prespecified comparisons. Reassess with independent morphology measures before attempting E2 associative-learning protocols. Maintain matched information/compute controls, split integrity and independent scientific qualification.

## Local session evidence identifiers (SHA-256)

These digests were recomputed from session-mounted source/results files on 2026-10-29; files are not committed in this PR. They enable later identity matching **only if those original bytes are durably retained and independently accessible**. They are not original-source Git commit pins or independently authenticated custody.

| Original relative session path | SHA-256 |
|---|---|
| `e1a/run_e1a.py` | `a9d53532e91c1920efdd1900bdf7a38786f99848d3efd5816ce2ed32c3b39dab` |
| `e1a/results.json` | `4f3def58a8c289ee4499f2dff4f494fba386e50427ecfa31a5d872a8944d5996` |
| `e1a/results_1200.json` | `369b4d6a3c4645afd51302b3510bf74d9784a5554d2ea9ba03ebddc9a902983d` |
| `e1b/run_e1b.py` | `0f5fa7f84606fc73dcfabc6ee531eb76962ba73f165c5b1782ef22822fa96ae0` |
| `e1b/results.json` | `24fbb9b186dffbddc9a59a94134fb3f39e03efa1a9ee088beff585aece718c68` |
| `e1c/run_e1c.py` | `317e55c46fa7d0d8068aea3274d5ccc8374e53443f2872038090122ce79c7e29` |
| `e1c/results.json` | `a676dd6e5f3339c5c4168562f875a4430193d2f1af3d20081fc56535f3aceab1` |

**Integration boundary:** This is a human-readable advisory report intended for later retrieval. It does not demonstrate FORGE automated ingestion or eligibility for scientific selection. FORGE-native FSA and independent qualification remain separate.
