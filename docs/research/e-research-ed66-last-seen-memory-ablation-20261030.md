# E-D66 — Last-observation memory under 40-step cue masking (2026-10-30)

**Execution PASS, limited synthetic memory benefit OBSERVED; native emergent intelligence NOT DEMONSTRATED.**

12 fresh exploratory FIT seeds 41000–41011, 2 environment resource-source shifts (clustered/sweeping), 5 policy arms (trained TD, trained TD+last-observed state, trained contextual bandit, bandit+last-observed state, no-update Q), total **120 frozen-policy evaluations**. All trained for 3 episodes on original E-C2 sources; evaluation had 40 consecutive masked time steps 20–59. On memory arms, preserve the agent's last visible 3-element discretized resource state and reuse it throughout that interval; otherwise provide a constant (0,0,0) cue. Masks and physics are identical across control pairs. Frozen Q values and no evaluation updates.

| Arm | Clustered mean harvest/action | Sweeping mean harvest/action |
|---|---:|---:|
| TD + last-seen observation | **0.0201999560** | **0.0206759617** |
| TD without memory | 0.0164456136 | 0.0164298752 |
| Bandit + last-seen observation | 0.0067669835 | 0.0087791247 |
| Bandit without memory | 0.0054900829 | 0.0061058780 |
| No-update Q | 0.0059581143 | 0.0070885893 |

Matched TD memory versus TD no memory: clustered **10/0/2** wins/ties/losses, +22.83% mean efficiency; sweeping **10/0/2**, +25.84%. Bandit memory vs bandit nonmemory: clustered **7/5/0**, +23.26%; sweeping **7/5/0**, +43.78%. Thus some benefit is from an elementary conventional cue-reuse mechanism, not necessarily learned memory.

Representative deterministic reruns (seed 41000, all arms x conditions) PASS; energy-ledger maximum residual `2.1714186004828662e-11`. Elapsed time 12.363 s. E-D62 source SHA-256 `3427467482c768442a4ab7b0472543fe5857c321f02ee25546d06d50a89c9f27`. Local script `/mnt/data/e_research/ed66/run_ed66.py` SHA-256 `c3537d40f969b6d7cec8ef8d5440cbe6ccb6ab8338c4001a7353e52100e19ad0`; JSON `/mnt/data/e_research/ed66/results.json` SHA-256 `343dfc8a9bbc299d808eeb663a37d8bf6ada1208d4df1daebfbe79e66b9dbcf6`. These original bytes remain session-local and are **not independently archived on GitHub**.

**Scientific limits:** Human-coded last-seen cue cache, not autonomously learned persistent memory. Same 16x16 synthetic E-C2 ecology, manually selected shifts/masks, 12 exploratory seeds, no sealed holdout or independent witness. No conventional recurrent learned memory or belief-state control and no native Wingless/Yggdrasil. E-D65 first-40 masking and E-D66 middle-40 masking are DIFFERENT interventions and must not be compared directly as if matched. No scientific first-use / FORGE model selection. DoorKey independent runner blocker #1245 unaffected.

**Next useful experiment:** compare last-seen caching against a conventional decaying-belief estimate or recurrent value tracker on matched corruption/delay patterns. Preserve all negative findings. FORGE production autonomy untouched.