# E Research E2-P1 — FIT-only chemical history pilot (2026-10-29)

**Status:** Isolated session execution PASS for numerical validity and reproducibility; **association learning UNVERIFIED / evidence NOT SUPPORTED**. Documentation only, not FORGE-run FSA evidence, scientific first-use or model-selection authorization.

## Execution

64×64 Gray–Scott reaction–diffusion vs passive diffusion, 12 original FIT seeds, two history assignments (paired vs unpaired), 2 model modes = **48 trajectories**. Explicit Euler dt=0.25, 4 substeps per nominal unit, 240 nominal time units. Identical cue A at times 40/70/100/130 and probe at 200; same consequence dose but consequence port differs between histories. Output observation at t=199 and t=210. Counterbalancing of environmental mapping not yet complete. No evolution, learned weights, hidden evaluator or HOLDOUT.

Numerical validity at intermediate substeps **PASS**; deterministic replay **PASS**. Source/results were generated in isolated session, not by FORGE CI.

| Metric | Gray–Scott | Passive diffusion |
|---|---:|---:|
| Median paired-vs-unpaired post-minus-pre output response contrast | -0.00000859332 | -0.00170271504 |
| Median preprobe output concentration history contrast | 0.00001192797 | 0.02106652655 |
| Fraction with preprobe output state differing between histories | 1.0 | 1.0 |

**Negative interpretation:** All paired comparisons have different output chemical states *before* the probe. Passive diffusion shows substantially larger history-response contrast than the reactive system. This pilot therefore fails to distinguish direct residual chemicals/relaxation from genuine learned cue-to-outcome association. No history-dependent predictive learning claim is warranted. Output port exposure differs between histories, so the current pilot is additionally confounded by location-specific prior stimulation.

## Local original-byte digests (SHA-256)

- `e2p1/run_e2p1.py`: `95e087e6389a71c6b3b940722ea45ebb5822d222f92972705c9587c66a9b6c1f`
- `e2p1/results.json`: `11948172a88c91fdf14e4039050d85c317a6e5abbe9172d64f27747241f991bd`

These originals remain session-local and are not committed to this repository; hashes alone are **not** independent custody or scientific acceptance.

## Next gate

E2-P2: control port-specific residual chemical confounding, establish independent washout and cue-only baseline, preregister response statistic, test history-reset/sham exposure and balanced stimulus order. Use only FIT; do not open or create sealed heldout first-use sets without existing scientific authority. Preserve all failures and negatives.

**Plain English:** The materials carry residue from the past, but we have not shown that they predict anything. Do not feed this into FORGE as a scientific learning improvement.
