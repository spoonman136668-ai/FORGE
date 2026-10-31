# E-D82 — History-span × model-capacity factorial (2026-10-30)

**Engineering execution PASS. Transfer-failure mechanism UNRESOLVED. Scientific first-use NOT ACCEPTED.**

Ran 24 actual local train/evaluate configurations: history windows 6,12,24 × hidden widths 18,54 × curricula original-only and ecology+oscillator × initialization seeds 820,821. All use original E-D80 training/evaluation stream functions (20 unique training sequences, 40 examples, 35 Adam steps); evaluated on 16 NARMA-like fourth-process synthetic seeds 50000–50015 and three previously tested mask schedules. This is **not** a fresh held-out benchmark. Factorial varies parameters jointly with history and width; it does not hold parameter count fixed. Equal update counts do not imply equal FLOPs. No native Wingless/Yggdrasil model, independent external source or scientific witness.

| Window / width | Parameters | Original-only MSE | Two-family MSE |
| --- | ---: | ---: | ---: |
| 6 / 18 | 380 | **0.048423** | 0.055080 |
| 6 / 54 | 1136 | 0.050246 | 0.056550 |
| 12 / 18 | 704 | 0.061552 | 0.070787 |
| 12 / 54 | 2108 | 0.051494 | 0.060690 |
| 24 / 18 | 1352 | 0.049817 | **0.052142** |
| 24 / 54 | 4052 | 0.055771 | 0.058381 |

Original-only beats two-family on all six model configurations; longer history and larger width do not consistently improve transfer prediction. These outcomes do not distinguish distribution shift from optimization/representation limits. Model fitting medians across two repeats are ~0.054–0.172 seconds; evaluation ~0.005–0.009 seconds per fixed batch. Process peak RSS is 324376 KiB shared across all sequential trials, *not* per-model memory. Few timing repeats preclude reliable throughput ranking.

Original local experiment script `/mnt/data/ed82_run.py` SHA-256 `3463b1ea41f5169887596309339a76e8dc2996a64cdf2e88580744e1e6aa3b42`; raw result `/mnt/data/ed82_results.json` SHA-256 `9dca740302a3dc6eec6f79b4c71dd997f1e13ee8226527a43c48752da346876a`. **Original experiment bytes are local, not independently authenticated repository custody.** This GitHub commit is advisory findings only.

Next meaningful scientific step: original independently sourced benchmark, held-out task-family split, exact training/FLOP budget checks and deterministic replay; stop tuning against previously inspected NARMA family as if it were untouched. No FORGE owner/autonomy/controller changes.