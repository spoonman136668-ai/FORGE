# E-D79 — third-family excluded synthetic transfer (2026-10-30)

**Engineering execution PASS. Exploratory third-family transfer improvement observed; independently qualified scientific intelligence NOT demonstrated.**

## Design
Ran `/mnt/data/ed79_run.py` with unchanged E-D76 GRU (2,138 params) and 12-step history MLP (2,108 params); fixed 3 initialization seeds 790–792, 35 full-batch Adam steps, 40 examples from 20 unique training sequences per condition. The original-only arm uses 20 E-C2 resource streams; the two-family arm uses 10 E-C2 and 10 E-D77 oscillator/telegraph streams (seeds 48000–48009). Both evaluate on 16 entirely excluded new **synthetic renewal-switching** streams (seeds 49000–49015), which feature random dwell times, abrupt level resets and low stochastic drift rather than either original ecological source or periodic oscillator. Exactly the same three already explored mask schedules are applied to both models and the last-observation cache. Neither architecture sees third-family examples in training. Third family was created by the experimenter for this gate, **not an independently frozen source-pinned benchmark**. Example counts and optimizer steps match, not training FLOPs or wall-clock cost.

| Model/curriculum | Shifted20 MSE | Longer50 MSE | Late25 MSE | Mean of three |
| --- | ---: | ---: | ---: | ---: |
| GRU original only | .09224118 | .08961752 | .10248547 | .09478139 |
| GRU two families | **.07940806** | **.08055934** | **.09297599** | **.08431447** |
| History MLP original only | .08759973 | .08713488 | .09621687 | .09031716 |
| History MLP two families | **.07169554** | **.07306781** | **.08247640** | **.07574658** |
| Last-observation cache | .12358941 | .14154086 | **.07191301** | .11234727 |

Two-family training reduces aggregate mean error about **11.0% for GRU** and **16.1% for MLP**. The history MLP outperforms the GRU across all three schedules in the diversified condition. The last-observation cache beats both trained models on the late25 schedule. This is **predictive error**, not closed-loop reward, learned causal structure or native model autonomy.

Local source `/mnt/data/ed79_run.py` SHA-256 `6bd4157572a554219ccd8dcfdfdc407b8c4cde4569a6ae54edf335925cd0c4ae`. Raw JSON `/mnt/data/ed79_results.json` SHA-256 `7ff4ed43f0c2f4f0c1c79403c32f6073abd4928ade8cc564be882c2d38718213`. Original execution files remain local, not independently authenticated in GitHub. The third family was designed after prior research; the evaluation is exploratory, not first-use independent. No non-transformer Wingless/Yggdrasil native model was trained, no full source-pinned external environment, no independent witness and no FORGE scientific acceptance.

**Next meaningful gate E-D80:** freeze the third-family protocol and add a fourth independently sourced unfamiliar-family check, compare against conventional learned controls with compute/memory accounting, and move to closed-loop rewards only with qualified original-source evidence. Do not promote exploratory findings or interrupt FORGE autonomy.