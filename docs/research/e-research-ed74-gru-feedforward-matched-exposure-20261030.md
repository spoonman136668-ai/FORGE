# E-D74: GRU vs feedforward, equal exposure and steps (2026-10-30)

Engineering **PASS**, scientific advantage **UNVERIFIED**. Executed original E-D73 synthetic observation generator with 20 training seeds and 8 disjoint evaluation seeds. Both controls trained on the same 40 visible/masked sequences for 35 Adam steps, using a new deterministic seed 740. GRU: 2,138 parameters, 0.606 seconds; feedforward MLP: 290 parameters, 0.064 seconds. **Not parameter-, FLOP-, or wall-time-matched.** No policy rewards measured.

| Unseen mask schedule | GRU MSE | Feedforward MSE | Last-seen cache MSE | GRU per-seed wins vs MLP |
| --- | ---: | ---: | ---: | ---: |
| shifted 20 steps [30,50) | 0.01762110 | 0.01848263 | 0.03027344 | 5/8 |
| longer 50 steps [10,60) | 0.01640381 | 0.01743081 | 0.02968750 | 6/8 |
| late 25 steps [45,70) | 0.02213828 | 0.02356071 | 0.02421875 | 5/8 |

**Limitations:** 8 exploratory evaluation streams; new mask schedules within same custom synthetic resource process, not an independent task-family transfer. Sequential GRU has substantially greater training cost. Feedforward model predicts from current visible/masked cue and visibility bit only; no matched history window. This is not an equal-information conventional baseline. E-D74 source and raw results are local session files (`/mnt/data/ed74/run_ed74.py` and `results.json`), **not independently archived or attested**. The script imports E-D73 and therefore executes its original training at import time before fitting both E-D74 comparators; reported timings are only model-specific E-D74 fitting, not the end-to-end cost. This does not prove efficiency or robust learning.

**Next:** compare to history-window MLP and conventional recurrent alternatives with recorded total compute and frozen independent evaluation; do not advance FORGE scientific selection. No FORGE controller or autonomy modifications.