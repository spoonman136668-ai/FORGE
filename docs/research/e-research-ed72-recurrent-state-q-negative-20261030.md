# E-D72 — Trained tabular recurrent-state control, negative result (2026-10-30)

**Local evaluation completed: 96 episodes. Native/independent scientific qualification: NOT GRANTED.**

E-D72 adapted the retained E-D69 test harness to maintain an agent-local 3-component recurrent cue `h_t=(round(.65*h_prev[0]+.35*obs[0]), round(.65*h_prev[1]+.35*obs[1]), obs[2])`, with frozen learned tabular Q-values over cue state. During observation masking the controller reuses its latest h. The Q-values are trained using standard TD updates over 3 original-source training episodes; **recurrent update weights are fixed by the researcher**. Therefore this is a *trained recurrent-state Q policy*, NOT a learned RNN, GRU or LSTM. Reference policies: trained TD last-observation cache, trained TD decaying observation cache, and same recurrent-state Q with TD update disabled. All 96 frozen evaluations used new exploratory seeds 44000–44005, clustered/sweeping evaluation resource-source shifts and mid-episode cue masking of 40 and 60 steps. Same original synthetic E-C2 physics, energy conservation, source representation and episode horizon.

Mean harvest/action:

| Shift/mask | TD last | TD decay | Recurrent-state Q | Recurrent no updates |
|---|---:|---:|---:|---:|
| Clustered/40 | 0.019382144339 | 0.016275287331 | 0.006101085217 | 0.006203080074 |
| Clustered/60 | 0.013645208545 | 0.013358112912 | 0.004704517705 | 0.006203080074 |
| Sweeping/40 | 0.022567739885 | 0.019755728541 | 0.010814813918 | 0.007897933825 |
| Sweeping/60 | 0.014891936275 | 0.014055749441 | 0.007180776472 | 0.007897933825 |

Energy-accounting maximum residual `2.1716097670099188e-11`. Local runtime 10.477 seconds. Source `/mnt/data/ed72/run_ed72.py`, results `/mnt/data/ed72/results.json`; run readback: 96 rows. The tested variants are exploratory, not a sealed holdout and have no independent GitHub source/result custody. No full deterministic rerun performed in this gate. The recurrent-state Q arm is not competitive versus last-seen cache in any evaluation condition; it is better than its no-update arm only in sweeping/40, indicating no consistent robust learning effect for this design. No independent scientific acceptance or generalized intelligence demonstrated.

**Next test:** train and compare a genuinely *learned* recurrent transition (e.g. a small GRU or recurrent model-free learner), with exact matching training episode count, observations, seeds, compute/resource metrics and conventional memory controls. Do not mislabel the existing hand-coded exponential smoothing as a trained recurrent network. Keep FORGE autonomy/controller unchanged; original official DoorKey source runner remains independently blocked #1245.
