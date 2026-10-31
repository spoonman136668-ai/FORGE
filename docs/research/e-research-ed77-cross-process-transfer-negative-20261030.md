# E-D77 — Cross-process synthetic transfer stress (2026-10-30)

**Local engineering execution PASS; trained predictors FAILED to outperform the last-observation cache. Independent source-pinned external task qualification NOT PERFORMED.**

## Design
Reused E-D76 training traces and its unchanged GRU (2,138 parameters) and history-window MLP (2,108 parameters), 35 Adam steps on 40 original-resource visible/masked training sequences, with three fixed initializations (750, 751, 752). Frozen evaluation on **16 unseen, newly constructed synthetic oscillator/telegraph observation streams** with periodically reversed drift and stochastic second-channel dynamics, seeds 47000–47015. Compared identical input masks with an untrained last-seen cache. This **is a new synthetic process** but not independently sourced or original external MiniGrid/CausalGym benchmark, nor a sealed held-out source family. 3 trained instances per model; three masking schedules evaluated on 16 streams each. No closed-loop policy reward, task action success or scientific first-use.

| Mask schedule | GRU mean MSE | History MLP MSE | Last seen MSE |
|---|---:|---:|---:|
| Shifted 20 | .0889006560 | .0752236224 | **.0554266468** |
| Longer 50 | .0945436007 | .0902630643 | **.0403395410** |
| Late 25 | .0951203168 | .0856279917 | **.0364728188** |

Across three repeat × 16 seed samples, history MLP was lower MSE than GRU in **38/48 shifted**, **23/48 longer**, **32/48 late** paired stream comparisons. Aggregated mean MLP better in each schedule; the simple cache was better in all three aggregate means. This is a cross-process failure of trained predictors relative to a simple conventional control, not a native Wingless/Yggdrasil evaluation.

## Provenance
Direct execution in isolated local container. New source: `/mnt/data/ed77/run_ed77.py`, SHA-256 `6391725c018a9c001f092043b034242d8785e3709ec15305e65855e291c92f7b`. Raw JSON: `/mnt/data/ed77/results.json`, SHA-256 `b06b0bcfbf399d6bfeab40826cb1b939e7920798d0400f82247ef5c7c425186e`. These are **session-local** and not independently authenticated GitHub source/results custody. Source generation uses a fixed new process and fresh seeds; designs selected during research, not a sealed independent holdout. Prior E-D76 source import only obtains training data and model class definitions, not an additional optimizer loop.

## Conclusions
No source-pinned external benchmark result, no accepted unfamiliar-family transfer, no scientific first-use, no native research model integration. Do not claim a general-purpose recurrent memory breakthrough. Next true gate requires an authorized independently sourced environment/runtime, frozen protocol and equal-information nonrecurrent controls; fix direct GitHub source/push access before custody claims. Protect existing FORGE autonomy and research isolation.
