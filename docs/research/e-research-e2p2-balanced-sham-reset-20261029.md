# E Research E2-P2 — balanced exposure, sham and reset FIT diagnostic (2026-10-29)

**Status:** Engineering FIT PASS; cue-dependent associative prediction NOT SUPPORTED; scientific learning UNVERIFIED. Advisory-only, no FORGE first-use, selection, FSA custody or runtime changes.

## Executed isolated local test

Reused the source-defined Gray–Scott vs passive-diffusion 64×64 periodic dynamics and existing FIT seeds **12001–12006**. Counterbalanced two consequence-port orderings (ABAB/BABA), each containing identical counts/doses of cue and outcome exposures at t=40,70,100,130. Compared probe-cue, cue-absent sham and full-state-reset-before-probe conditions at t=200, with responses through t=210. Four Euler substeps of dt=0.25 each nominal step; same observed output-region difference for all conditions. **6 seeds × 2 histories × 2 dynamics × 3 conditions = 72 trajectories.** Deterministic replay PASS; finite/nonnegative intermediate state checks PASS.

### Median absolute paired-history contrasts

| Dynamics | Probe mode | Before probe | After probe | Change, post minus pre |
|---|---|---:|---:|---:|
| Gray–Scott | cue | 0.0000225117 | 0.00000698224 | 0.0000155295 |
| Gray–Scott | sham (no cue) | 0.0000225117 | 0.00000698224 | 0.0000155295 |
| Gray–Scott | full reset + cue | 0.0000225117* | **0** | 0.0000225117* |
| Diffusion | cue | 0.00538607 | 0.00446257 | 0.000923500 |
| Diffusion | sham | 0.00538607 | 0.00446257 | 0.000923500 |
| Diffusion | full reset + cue | 0.00538607* | **0** | 0.00538607* |

*Reset rows' pre-probe value was sampled before the reset at t=200. Their apparent change is **not** a learned cue response; comparing post-probe states after reset shows 0 between histories. Absolute values in the change column are magnitude summaries; signed differences may be opposite.*

## Scientific reading

The chosen readout's **paired-history contrast was numerically identical with and without a cue** in both dynamics (on the printed precision, and exact in the session measurements for the compared statistic). This is expected because the cue is applied at a spatially separate input port and the measured antisymmetric output-port difference follows identical evolution in paired histories at these settings. No cue-contingent associative learning shown. Before-probe differences survive balanced *counts* due to different ordering of the same outcomes, so counterbalancing counts does not eliminate residual-state confounding. Passive diffusion's history contrast is orders of magnitude larger than Gray–Scott's. Reset removes post-probe differences because the state is replaced identically for each history, not because a learned mechanism was selectively deleted.

**Scientific conclusion: do not call this associative learning, predictive cognition, or autonomous memory improvement.** This was a FIT-only negative, not held-out falsification of all possible local chemical memory mechanisms.

## Provenance and limits

- Script: isolated session `/mnt/data/e_research/e2p1/run_e2p2.py`, SHA-256 `61c76c6df20662aaea74ac4bc9b6e36c266b57a95097a3771e5c1bcdcacab42f`.
- Raw results: isolated session `/mnt/data/e_research/e2p1/e2p2_results.json`, SHA-256 `f2e59f2e7b068b2fbe030a5f137d0e9cabab18eb99c599d8896ffe931c8ce1fa`.
- These original bytes are not in the GitHub repo or independent scientific archive; digests are **not** proof of remote custody. No validation or held-out cohort, independent first-use witness, randomized environment families or formal statistical efficacy test. No completed washout-time certification; persistent pre-probe difference is a fail for the simple intended attribution.

## Next eligible experiment

E2-P3: test cue-dependent anticipatory signal against paired **sham** in a symmetric, counterbalanced readout, with a prespecified minimum effect and independent washout diagnostics; if the unmodified two-species system fails, close its FIT associative-learning claim. A variant with a dedicated slow memory species must have a distinct name and control for explicit memory capacity, not be mislabeled spontaneous emergence.

**Plain English:** A history signal exists, but the cue does not cause it; ordinary chemistry explains it without learning.
