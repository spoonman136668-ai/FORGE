# E-D64 — frozen TD-policy transfer under shifted resource sources (2026-10-30)

**Local execution PASS; bounded transfer effect OBSERVED; independent scientific acceptance NOT GRANTED.**

## Experimental design
Reused original E-D62 Q-learning source at SHA-256 `3427467482c768442a4ab7b0472543fe5857c321f02ee25546d06d50a89c9f27`. Via AST, added a TD-update toggle and evaluation-only resource source-shift toggle to the `q_episode` function. Trained under **original dynamics** for three episodes (same seed) with TD updates enabled or disabled. Frozen evaluation (`test=True`, epsilon 0, no TD updates) is run in original, static clustered resource centers, and deterministic sweeping centers. The evaluation-only source change affects regenerating resource location, not agents' observations, reward or energy ledger rules. Twelve new exploratory seeds 39000–39011, 3 evaluation families × 2 TD-update arms = 72 evaluation trajectories. This is **exploratory synthetic E-C2**, not a sealed independent holdout, and no trained conventional competitor besides the zero-update ablation is included.

| Evaluation resource pattern | TD trained mean harvest/action | No-TD-update mean | TD/no-update | Paired wins/ties/losses |
|---|---:|---:|---:|---:|
| Original | 0.0281627543 | 0.0067162341 | 4.19× | 12/0/0 |
| Clustered | 0.0170761738 | 0.0059524871 | 2.87× | 10/1/1 |
| Sweeping | 0.0214221553 | 0.0068701877 | 3.12× | 12/0/0 |

Mean TD advantage declined 39.37% clustered, 23.93% sweeping compared with original, but stayed positive in the exploratory altered resource sources. Representative deterministic rerun assertions covered both update arms for one seed per condition (6/6) and passed. Maximum energy-accounting residual `2.1728396859543864e-11`; 72 evaluations, wall runtime approximately 8.791 seconds.

## Interpretation / limitations
A human-coded tabular Q-controller benefited from TD updates on resource patterns beyond those encountered in training. This is **narrow policy carryover across reward-source geometries within the identical 16×16 synthetic environment**, not robust causal representation, independently acquired concepts, different task-family generalization or native Wingless/Yggdrasil intelligence. The zero-update arm is a diagnostic control, not a trained greedy or model-based baseline; do not claim superiority over those. Original code and results remain local, not source-authenticated in FORGE. Keep draft advisory only and scientific first-use unapproved. DoorKey genuine source-pinned execution separately blocked (#1245).

Code local: `/mnt/data/e_research/ed64/run_ed64.py`; raw results local: `/mnt/data/e_research/ed64/results.json`. No FORGE autonomy changes.
