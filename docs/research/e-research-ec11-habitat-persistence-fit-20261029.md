# E Research E-C11 — post-birth habitat persistence FIT test (2026-10-29)

**Status:** Isolated CPU engineering PASS; habitat persistence benefit observed in FIT under the implemented physics; **descendant-specific learning / evolved construction UNVERIFIED**. No FORGE FSA scientific acceptance, first-use, native-model promotion, or autonomy modification.

## Actual execution

Source-derived from previously local E-C10/E-C9 20×20 coordinate/site generator; this is a **fixed-site** ecology, not independently navigating or evolving organisms. Single local nutrient reservoir; fixed harvesting and programmed two-agent energy-split reproduction threshold 1.6. Six reused FIT seeds 41000–41005 × three site cases × three development viability configurations × four arms = **216 trajectories**, each 300 nominal steps.

Fixed intervention: construction costs 0.08 energy and 0.12 local material, creates 0.22 habitat state; retained habitat decays by 0.998 each step and boosts replenishment by 1+0.7h. Arms: persistent construction, **habitat reset immediately at the first offspring birth**, equal-cost construction sham, and no-cost sham. Same weather/seed stream and local harvesting physics. Reset happens on first birth only; if no birth occurs the persistent/reset trajectories match, correctly making the comparison non-informative about descendant inheritance.

Numerical resource+energy conservation maximum abs residual **1.149080830487037e-13**, finite/nonnegative constraints PASS, first-row deterministic replay PASS, local execution wall 0.383 seconds. Session peak process RSS 96024 KiB (process-wide).

### Results: 18 FIT seed/site pairs per configuration

| Supply / metabolism | Births present: retained / reset / matched sham | Median retained minus reset total harvested | Median retained minus reset harvest after retained-arm first birth | Median retained minus matched-cost sham total harvested |
|---|---:|---:|---:|---:|
| 0.018 / 0.025 | 8 / 8 / 2 | 0 | 0 | +0.762113 |
| 0.008 / 0.012 | 13 / 13 / 4 | +0.180630 | +0.180630 | +0.390630 |
| 0.018 / 0.012 | 18 / 18 / 18 | +0.663838 | +0.663838 | +0.738299 |

**Critical interpretation:** Under viable configurations, retaining a pre-built habitat after the first birth delivers more total harvesting than clearing it at the first birth, despite equal initial construction costs. That establishes a local, programmed **environmental persistence affordance**. It does **not** isolate offspring harvest: the measured post-birth harvesting includes both parent and offspring; no parent-only or progeny-only outcome was logged. Comparison to sham can change reproduction timing and cumulative population metabolism. There are no adaptive actions, genetic selection, independent novel world transfer or causal learning mechanisms. The enhancement itself is specified in the renewal equation; no claim that it emerged autonomously.

## Original source and reproducibility

- Session source: `/mnt/data/e_research/ec11/run_ec11.py`
- Original machine-readable results: `/mnt/data/e_research/ec11/results.json`
- Both remain **outside this documentation-only GitHub commit**. GitHub report is insufficient alone to independently reproduce the result. Do not call it FORGE-owned original science, first-use evidence or qualified acceptance.

## Next eligible gate E-C12

Predeclare **offspring-only** resource intake and survival after birth; compare habitat-retained versus habitat-reset paired at equal offspring start state and fixed birth time or disclose any loss of ecological authenticity from forced matching. Separate programmed physical affordance from evolved ability to choose useful construction actions. Add nonconstructors, random placement and conventional reactive construction baselines with cost and observation parity. If the effect is solely prewired environmental renewal, classify engineered niche inheritance, not emergent native intelligence.

**Plain English:** Keeping a constructed habitat around after a child is born can make the family harvest more. But we haven't measured whether the *child specifically* benefits, and no organism learned to build.
