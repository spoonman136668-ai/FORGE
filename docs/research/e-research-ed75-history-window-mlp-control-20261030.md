# E-D75 — Matched-parameter history-window MLP vs GRU (2026-10-30)

**Actual isolated local engineering execution PASS. Recurrent model superiority NOT demonstrated.**

Both models trained on the same 40 synthetic visible/masked observation sequences over 35 Adam update steps. GRU 2,138 parameters; 12-step history-window MLP 2,108 parameters. Both see the same 3-feature stream with a visibility bit and the same original synthetic train/evaluation seeds as E-D74. This is closer to information and parameter parity, **not equal FLOPs or total compute**. Fixed seed for this experiment: 750. All results from eight evaluation streams (46000–46007) and three unseen mask windows. No policy rewards or native model evaluation.

| Schedule | GRU MSE | History MLP MSE | Last-observation MSE | GRU wins / 8 |
|---|---:|---:|---:|---:|
| Shifted 20 | 0.01695923 | 0.01923154 | 0.03027344 | 6 |
| Longer 50 | 0.01665740 | **0.01483177** | 0.02968750 | 3 |
| Late 25 | 0.02091328 | 0.02188289 | 0.02421875 | 5 |

GRU model-only training time 0.6124s vs history MLP 0.0914s. Model evaluation across the batch of 24 streams 0.03449s vs 0.00329s. These are single-run wall-clock measurements not independently characterized with repetitions, CPU limits or full profiler; underlying E-D73 module performs a separate model train upon import, so end-to-end time of the script (3.5s) includes that incidental training. End-to-end script timing **is not** a fair comparison between the two new models.

E-D75 local script: `/mnt/data/ed75/run_ed75.py`; raw JSON: `/mnt/data/ed75/results.json`. Original evidence bytes not separately custodied or independently witnessed on GitHub. No science acceptance. A negative finding for universal recurrent advantage: strong history MLP beats GRU on the longest mask and is cheaper in these runs. Not a rejection of general recurrence or robust transfer.

**Next gate:** Remove unneeded import-time training, measure repeated exact-key full-pipeline costs with memory and FLOP accounting, and independently evaluate a frozen, unseen resource/task family against stronger controls. No FORGE production autonomy or native Wingless/Yggdrasil changes.
