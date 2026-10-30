# E Research E-D19 — short-memory nonstationary-probe FIT (2026-10-29)

**Actually executed locally. Engineering PASS; conventional shorter-window adaptation improved; fully recovered optimal probe choice NOT SUPPORTED.** This is a documentation-only advisory note. No FORGE autonomy, runtime, controller, owner, native model, selection or scientific admission change.

## Actual experiment
Read and imported unchanged original E-D18 generator and physics from the isolated session. Same hidden halfway reliability change after 180 of 360 sequential trials: probe A (.85 to .55), cost 1; probe B (.60 to .90), cost 3. Two binary gate interventions cost 8 energy total, one first gate hardcoded successful, harvest 12 if second choice correct. Optional bought probe identifies hidden binary structural change with its environment-specified reliability. Probe fidelity is only learned after action-feedback. All arms use same public choice/cost interface; the oracle sees ground-truth reliabilities and is an upper bound, not a fair competitor. Seeding: 16 new unsealed FIT seeds 73000–73015 × 360 episodes × eight policies = **46,080 episodes**.

Three conventional new baselines:
1. **Short-window UCB** last 32 selected-probe accuracy samples, empirical Beta(1,1) frequency and handcrafted optimistic upper bonus coefficient .65.
2. **Discounted Thompson** exp-discount accuracy observations by .97 age and draw Beta posterior values.
3. **Change-sensitive UCB** if last 12 feedback outcomes diverge from older observed accuracy by more than .22, reduce window from 48 to 16; optimistic coefficient 1.0. Does not have access to true shift time.
Existing controls: original E-D18 UCB and Thompson using unchanged decision routines; fixed A; never purchase; privileged known-reliability oracle. Policy-specific random seeds; matched environmental outcomes within seed/time, fixed costs, all energy/material ledger assertions and exact full-seeded replay PASS. Original algorithms were authored heuristics/standard exploration; **no novel native cognition** tested.

| Policy | Prechange mean net | Postchange mean net | Postchange B selections /2880 | Last 60 postchange B /960 |
|---|---:|---:|---:|---:|
| Short-window UCB | +1.225 | -0.99653 | 1903 | 797 |
| Discounted Thompson | +0.98368 | -1.31319 | 1340 | 704 |
| Change-sensitive UCB | +1.225 | -1.55139 | 1202 | 660 |
| Original UCB | +1.225 | -1.95000 | 786 | 482 |
| Original Thompson | +0.99062 | -2.33125 | 243 | 181 |
| Always A | +1.225 | -2.49583 | 0 | 0 |
| Never probe | -1.90833 | -1.85000 | 0 | 0 |
| Privileged oracle | +1.225 | -0.12917 | 2880 | 960 |

The stronger short-window strategy buys probe B in 18/480 cases in the first 30 postchange episodes and 797/960 in the last 60: adaptation happens gradually, not instantly. This test finds a *reduced postchange regret relative to original UCB*, but remaining large gap to privileged oracle. Seeded environments are a single synthetic nonstationary family with deterministic change at t=180, no independent heldout mechanism or source qualification. Sixteen world seeds, not 46,080 independent worlds; treat episodes as time-correlated.

**Local evidence:** `/mnt/data/e_research/ed19/run_ed19.py` SHA256 `73c44883797bcc5ea3c44fa64c723e2f69b91a92493563b991ca5ed5a68a5962`; `/mnt/data/e_research/ed19/results.json` SHA256 `66689192f823464339b1826028d73a5b8ee1f8514fd8d82f2ce65d24e192b460`. Those files and the imported E-D18 dependency are session-local, **not part of this documentation-only GitHub commit**, so independent reproduction, authenticated original source custody and scientific first-use remain UNVERIFIED. Execution 1.822s process-wide peak RSS 103448 KiB (not independent scientific resource qualification).

**Gate decision:** E-D19 engineering PASS, **conventional adaptive-memory improvement SUPPORTED on FIT**, new causal-intelligence advantage NOT SUPPORTED. No FORGE research-selection promotion.

**Next E-D20:** Freeze a genuinely different shift schedule (multiple unknown change times, gradual drift, abrupt reversals, altered costs and multiple observation actions), report per-seed confidence intervals and post-shift *regret/recovery latency*, compare matched adaptive memory versus conventional change-point Bayesian and fixed policy; do not tune on target results. Require remote custody of original executable and sealed first-use before scientific acceptance.

**Plain English:** Shorter-memory exploration switched toward the better clue faster after conditions changed. But it still lost resources and never caught up with a controller that already knew the correct answer.
