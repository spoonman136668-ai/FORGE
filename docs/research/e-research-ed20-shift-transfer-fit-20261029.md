# E Research E-D20 — unfamiliar nonstationarity FIT (2026-10-29)

**Engineering PASS; general reliable adaptation to changing reliability NOT SUPPORTED.** FIT-only conventional mechanism test, not native intelligence, scientific first-use, or FORGE FSA acceptance. Documentation-only advisory; no model, controller, owner, queue, selection or autonomy changes.

## Actual execution and source
Original local script `/mnt/data/e_research/ed20/run_ed20.py` SHA-256 **3d9f29fcdd6b18d66780fe3c38b20ba34c0e9e5f83b9e56384d45cae54ff01c3** and raw JSON `/mnt/data/e_research/ed20/results.json` SHA-256 **b3112619c3f3646f5c2f2ef3d51bae9221f2cf805d20be230aa56d857a5f3264**. Files exist in isolated session, **not included in this documentation-only commit**. Repo-only reproduction and independent custody/first-use UNVERIFIED.

Standalone deterministic synthetic environment derived from E-D18/E-D19 mechanisms with one automatically correct first barrier action, one hidden binary flip, two optional binary probes A and B, and a second barrier choice. The agent may purchase a probe, receives a noisy signal of flip, and learns probe accuracy through postchoice feedback only. Two construction steps cost 8 energy total, harvested reward 12 for success, probe costs paid in addition. Energy starts at 20 and material at 2; all per-step conservation assertions PASS. This isolates information acquisition, not general structural causal learning.

**Environments, selected before evaluating:**
- **Multiple reversals:** reliabilities A/B .85/.60 until episode 100, .55/.90 until 210, .85/.60 until 280, and .55/.90 thereafter. Probe costs 1/3.
- **Gradual drift:** A decreases linearly from .85 to .55, B increases linearly from .60 to .90 over 360 episodes. Costs 1/3.
- **Changing costs:** reliability changes at 180 from .85/.60 to .55/.90, probe costs A/B initially 1/3, then 2/2 at 120, then 3/1 at 240.

16 new but **unsealed FIT** world seeds 76000–76015 × 360 sequential episodes × three schedules × seven arms = **120,960 evaluated episodes**. Arm policies: short-memory UCB 32-observation window, discounted Thompson with .97 discount, simple change-trigger UCB, original 48-observation UCB, always A, never probe, and **privileged** known-true-probability oracle. All nonoracle controls receive identical public probe-cost information and action costs; oracle receives underlying reliabilities, not available to agents. Seeded full experiment exact replay PASS. 16 world seeds per schedule; 360 trials per seed are correlated and must not be treated as independent replicates. Process elapsed ~5.16 sec; peak RSS ~153,352 KiB (session-level, not independent resource validation).

| Schedule | Short UCB overall mean net | Discounted Thompson | Change UCB | Original UCB | Oracle upper |
|---|---:|---:|---:|---:|---:|
| Multiple reversals | -0.60694 | -0.73524 | -0.77326 | -0.73264 | +0.37778 |
| Gradual drift | -0.53681 | -0.64878 | -0.59826 | -0.61667 | -0.32778 |
| Altered costs | +1.02014 | +0.73906 | +0.84792 | +0.80417 | +1.26042 |

**Late-window diagnostics, final 90 episodes (16 seeds = 1440 cases):**
- Multiple reversals: oracle favors B on **1280** of 1440 cases; short-window UCB selects B **447** times, with late mean net -1.56250 versus oracle -0.19444.
- Gradual drift: oracle favors B on **1440**; short-window UCB selects B **558**, late mean net -1.40000 versus oracle -0.68333.
- Altered probe costs: oracle favors B on **1440**; short UCB selects B **1440**, late mean net +1.94167, matching oracle's +1.94167.

Important nuance: The first comparison counts purchases over the 1440 late episodes; because oracle does not favor B in all multiple-reversal late episodes, **447/1280 is not a paired classification accuracy statistic**. We report total B purchases and oracle B opportunities separately; records do not contain a paired exact match rate, so none is claimed. The changing-cost world is more favorable to B via *explicit cost changes*, making its adaptation less informative about identifying true observation reliability.

**Interpretation:** Short-window UCB is a strong conventional benchmark across these new synthetic development schedules and yields better mean net returns than the other tested nonoracle methods. It does NOT reliably identify the better observation under unfamiliar reliability reversals or drift, and even the oracle loses mean reward in drift conditions. No native model, independent source custody, held-out transfer, or general learning claim follows. The original planned model-comparison is purely conventional; no emergent algorithm was implemented. Normal-approx per-seed uncertainty fields and oracle-relative expected regret are preserved in raw JSON but are based on only 16 world seeds, not independent scientific inference.

**Next E-D21:** Stop repeated parameter sweeps on the same synthetic reward mechanism. Source a genuinely different causal task family and audit whether selective memory is useful against matched Bayesian change-point detection; freeze source and independently held-out families, original code custody and qualify before FORGE first-use. Keep the negative adaptation results intact.

**Plain English:** An agent reacts well when the price of information changes. It still struggles when information quality changes unexpectedly. This is a standard algorithm's limitation, not emergent reasoning.
