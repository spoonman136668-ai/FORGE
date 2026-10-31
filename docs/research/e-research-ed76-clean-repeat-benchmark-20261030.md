# E-D76 — Clean-source repeated GRU/history-MLP speed and prediction qualification (2026-10-30)

**Actual local engineering execution PASS. Recurrent efficiency/consistent accuracy advantage NOT demonstrated.**

The E-D75 module imported `run_ed73_masktrained.py`, which trains an unrelated original GRU during module import. This gate statically extracted the `trace` function from original E-D73 source and evaluated it in a minimal namespace with original E-C2 physics. **No incidental import-time training was executed**. Same 20 original training source seeds, 8 evaluation seeds, 40 visible/masked training sequences, 35 Adam update steps, model definitions, 12-step history, and three E-D75 previously evaluated masking schedules. Three initialization seeds 750, 751, 752; one CPU thread.

| Metric, median of 3 runs | GRU | History-window MLP |
|---|---:|---:|
| Parameters | 2138 | 2108 |
| Model fit seconds | 0.64327 | 0.10477 |
| Model evaluation seconds (24 sequences) | 0.04269 | 0.00380 |

Ratios of medians: MLP ~6.14× faster training and ~11.23× faster evaluation. The three fit times are GRU [0.66041, 0.62391, 0.64327], MLP [0.10477, 0.10400, 0.10865]. Model evaluation times GRU [0.03999,0.04269,0.06501], MLP [0.00380,0.00726,0.00358]. First-run GRU Python tracemalloc peak was 55 MB, subsequent much lower because PyTorch allocation/code warmup confounds Python memory measurement; **do not use tracemalloc as RSS / peak native memory**.

| Mask | GRU MSE (seed750 /751 /752) | MLP MSE |
|---|---|---|
| Shifted20 | .01696 / .02344 / .01970 | .01923 / .01898 / .02146 |
| Longer50 | .01666 / .01696 / .01674 | **.01483 / .01505 / .01607** |
| Late25 | .02091 / .02878 / .02503 | .02188 / .02156 / .02478 |

Limitations: timing samples are too few to characterize environment variance; equal examples and optimizer steps are **not equal FLOPs**. No full native RSS, energy use, held-out external task-family transfer, agent reward or scientific custody. Source and raw JSON are local `/mnt/data/ed76_run.py`, `/mnt/data/ed76_results.json`; not independently signed or stored as raw GitHub evidence. This is an exploratory repeat, not a first-use qualification. The tested shift schedules were used in earlier E-D74/75 analysis and must not be newly labeled as untouched holdouts.

Disposition: maintain recurrent memory as experimental, do not prefer it over cheaper competitive history MLP. Next scientific test requires genuinely novel source-pinned environment family, frozen evaluation and more complete memory/resource accounting without affecting FORGE autonomy.
