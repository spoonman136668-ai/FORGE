# E Research E2-M2 — local slow-chemical memory FIT result (2026-10-29)

**Classification:** isolated experiment engineering PASS; emergent cue-association NOT SUPPORTED; scientific acceptance UNVERIFIED. Advisory only, no FORGE autonomous controls or native-model changes.

## Actual experiment

Reused existing 64×64 periodic Gray–Scott geometry, chemical input and consequence ports, four balanced history events (t=40,70,100,130), probe t=200, readout t=199→210, 4 Euler substeps of dt=.25. Six original FIT seeds; two histories ABAB/BABA; cue/sham; 3 model variants = **72 trajectories**. All intermediate finite and nonnegative checks PASS; deterministic terminal replay PASS. Elapsed local runtime ~8.64 s.

Model variants:
1. **local:** third slow chemical field m updated at every site by local v production, local diffusion and decay: `dm/dt=.015*v²-.001*m+.002*Laplacian(m)`; local state coupling `dv/dt +=.001*m*v`. No externally supplied cue flag in the field update; no direct consequence-to-m update. This is an **engineered mechanism**, not spontaneous discovery.
2. **static:** identical third-field allocation/diffusion/decay and local coupling but no production; starting m=0.
3. **ablated:** no m dynamics or coupling.

Prespecified FIT readout: for each seed/mode, the difference of history (ABAB minus BABA) effects on post-minus-pre output-region v, between cue-present and cue-absent sham probes.

| Mode | FIT seeds | Max absolute cue-specific history interaction | Engineering |
|---|---:|---:|---|
| Local chemical field | 6 | **0 exactly** | PASS |
| Static field | 6 | **0 exactly** | PASS |
| Memory ablated | 6 | **0 exactly** | PASS |

The local field's history-contrast is ~1.809e-5 under both cue and sham; this is **not predictive cue learning**. A cue locally injected at the separate CUE region does not create a detectable cue-dependent output history interaction in this short probe window. The result is a negative **for this mechanism, readout, geometry and FIT horizon**, not a proof that local reaction–diffusion architectures cannot learn. No evidence of spontaneous causal association, communication or unfamiliar-family transfer.

## Original files and identity
- Source: local session `/mnt/data/e_research/e2m2/run_e2m2.py`, SHA-256 `590621302e22661dd0c111e55c7450b4ce2b5b2103d4c52fa288e30a436d6838`
- Original results: `/mnt/data/e_research/e2m2/results.json`, SHA-256 `e1f55f424c6cb7f2a3e9865a0959c3b7030952222e7ca0d37cb11b4ced3ba18d`
- Summary log: `/mnt/data/e_research/e2m2/summary.txt`, SHA-256 `d65e3c25757767b8c6e73c5e61aa80fb88e7b02b55fd7978fa0d72582c3511fa`
These original bytes are **not committed by this documentation-only report**; digests do not prove independent custody or enable reproduction without source retrieval. No FORGE native FSA, first-use witness, CI, heldout or research-selection qualification.

## Decision and next eligible gate

Reject the claim that this tested purely local slow field creates cue-conditioned association. Avoid optimizing the same readout indefinitely. **E2-M3:** conduct FIT-only **causal signal-propagation feasibility** (spatial distances, delay window and cue influence against sham), then compare a minimal *local* plastic coupling rule with an equally informed tabular/finite-state control only if the cue can reach the output without privileged wiring. Preserve negative results. No promotion or autonomous FORGE decision without normal authenticated science route.

**Plain English:** Local state storage is not enough. The earlier apparent success required a programmer-provided global cue link; removing it makes the learning signal disappear.
