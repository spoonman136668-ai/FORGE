# E-D80 — Fourth-process exclusion and diversity falsification (2026-10-30)

**Executed locally, engineering PASS; diversity-benefit generality FAIL on new process; independently sourced external benchmark NOT COMPLETED.**

## Design
Reused E-D76 original ecological observation generator and architectures (GRU 2,138 params; 12-step history MLP 2,108 params). Original-only condition uses 20 E-C2 streams; two-family condition uses 10 E-C2 and 10 E-D77 oscillator/telegraph streams. Both get 20 distinct streams / 40 visible and masked examples, 35 Adam updates with fixed initialization seeds 800–802. Frozen evaluation uses 16 excluded seeds 50000–50015 from a fourth locally implemented process, a bounded NARMA-10-style nonlinear recurrence with 10-step endogenous coupling. Three mask schedules (shifted20, longer50, late25). Neither curriculum contains this process. No training on the held-out evaluation seeds. *The process is locally constructed, not independently sourced, pinned, or independently locked before this gate.* The GRU and MLP are conventional learned predictors, not native Wingless/Yggdrasil agents.

| Model / curriculum | Shifted20 MSE | Longer50 MSE | Late25 MSE | Mean |
|---|---:|---:|---:|---:|
| GRU original | **0.05207506** | **0.04664395** | **0.04762781** | **0.04878231** |
| GRU two-family | 0.05374959 | 0.05029055 | 0.04955390 | 0.05119802 |
| History MLP original | **0.05388742** | **0.04886417** | **0.04905793** | **0.05060384** |
| History MLP two-family | 0.06145938 | 0.05792191 | 0.05745849 | 0.05894659 |
| Last-seen cache | 0.07426363 | 0.07479208 | 0.07442792 | 0.07449454 |

Thus training diversity *increased* mean error ~4.95% for GRU, ~16.49% for history MLP. On this fourth synthetic process, GRU's average MSE was lower than MLP for matched curriculum, but end-to-end compute and memory efficiency is not established. Whole-process peak RSS was measured as 329596 KiB, **not allocatable to one model**: sequential models, imported resources, data and allocator peaks share the process. No source-pinned external benchmark, closed-loop rewards, native model progress or independently witnessed scientific first-use.

Exact local source: `/mnt/data/ed80/run_ed80.py`, SHA-256 `e1a79a2d8a0516392c9d28d7d72697a4af0260061f31e319b3e9651bcedcbed1`. Exact local raw JSON: `/mnt/data/ed80/results.json`, SHA-256 `cf9fd53408ba52913efe149dd82334ea3d7333d8836c7212a1b5c97241ff06ad`. These raw artifacts remain local; a summary commit does not qualify independent source/results custody.

**Scientific interpretation:** E-D79's positive diversity result on renewal-switching did not extend to the new nonlinear delayed recurrence. This falsifies a broad claim of consistently beneficial diversity. Third-family transfer protocols are not a sealed evaluation (they were used in previous decisions), and fourth-family NARMA-style process is experimenter implemented. Required real externally sourced qualification remains pending. Next gate: rank per-seed paired effects and assess delay-specific failure; then independently source and source-pin external benchmark and original run before FORGE scientific selection. No FORGE autonomy, native model or production changes.
