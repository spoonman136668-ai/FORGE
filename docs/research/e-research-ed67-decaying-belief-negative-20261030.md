# E-D67 — Last-state memory versus decaying-belief control (2026-10-30)

**Actual local engineering execution PASS. Positive effect of last-seen state reuse in exploratory synthetic E-C2 ecology; distinct decaying-belief advantage NOT DEMONSTRATED. No scientific first-use acceptance.**

Executed `/mnt/data/e_research/ed67/run_ed67.py` against original E-D62/E-C2 mechanics with 12 new seeds (42000–42011), two evaluation resource shifts (clustered and sweeping), and 40-step mid-episode masking (steps 20–59). Seven frozen-policy arms per seed/shift: trained TD with no memory, last-state cache, or a decaying last-state estimate (rate 0.94 per hidden step), trained contextual bandit with the same three memory treatments, and zero-update control. 12 × 2 × 7 = **168 evaluation trajectories**, with three training episodes per learned arm per seed and no evaluation updates. Masks, resource physics, observations available before masking, and evaluation budget are matched.

| Arm | Clustered harvest/action | Sweeping harvest/action |
|---|---:|---:|
| TD, no memory | 0.011949984998 | 0.013339452442 |
| TD, last-state cache | **0.015280116281** | **0.017485652400** |
| TD, decaying belief | **0.015280116281** | **0.017485652400** |
| Bandit, no memory | 0.006614298527 | 0.007800526906 |
| Bandit, last-state cache | 0.007781348023 | 0.009136607392 |
| Bandit, decaying belief | 0.007781348023 | 0.009136607392 |
| No-update | 0.006968473166 | 0.007626717452 |

Paired last-cache minus no memory: TD clustered **11/0/1**, mean +0.003330131283; TD sweeping **12/0/0**, mean +0.004146199958. Bandit clustered **5/7/0**, mean +0.001167049497; bandit sweeping **5/7/0**, mean +0.001336080486. Last-cache minus decay: **0/12/0** in both resource shifts for TD and bandit, exactly identical recorded harvest values. No claim of different internal latent states or generalization. Max energy-ledger residual **2.1714186004828662e-11**; representative first-seed deterministic reruns for all 14 combinations passed. Wall time 17.448 s.

Local script SHA-256: `6fe56d47309ca0cf2d7ccae06fed4c791164d335ad9fe380afc9ef7e78c62875`; local raw JSON SHA-256: `9082d0752f3bcd50feec19bd4a170c43211c7792a9ea6250910aa5b46647715f`. Both files remain **session-local and not independently authenticated GitHub execution artifacts**. The decaying-belief variant is a simple hand-coded exponential attenuation of discretized cue bins, not a trained recurrent network or principled posterior filter. The exact-tied result may reflect rounding or policy insensitivity and requires action/hidden-state instrumentation before interpreting its mechanism.

Scientific interpretation: Basic observation retention is useful under this synthetic cue mask. More elaborate decay has not demonstrated any additional benefit. No new native Wingless/Yggdrasil learner, independently sealed holdout, original external environment, independently qualified mechanism, or FORGE scientific first-use. Separate DoorKey run/custody blocker #1245 unchanged; no FORGE owner, autonomy, or controller changes.

Next gate: inspect the actual action/state distributions to determine why last-seen and decay behave identically, then test longer masks or context-dependent hazards with stronger recurrent/belief-state controls rather than treating the equality as progress.
