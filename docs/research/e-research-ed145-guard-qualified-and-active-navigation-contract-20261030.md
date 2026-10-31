# E-D145 — Authenticated cue-localization guard and next experimental boundary

Source: existing FORGE draft PR #1194, commit `6a695ced9d1c3d0b26c022e4aefcabfc2f14a202`. GitHub Actions [run 41136948382](https://github.com/spoonman136668-ai/FORGE/actions/runs/41136948382): Linux job `124347127204` **PASS** and Windows job `124347126880` **PASS**. Original Linux log explicitly emitted `PASS_SPATIAL_CUE_ACQUISITION_SAFETY_AUDIT`.

| Exposed seed | Orientation loop | Candidate observed types | Original cue | Trace SHA256 |
|---|---|---|---|---|
| 84000 | closed | [5,6] | ABSTAIN_NOT_LOCALIZED | `1fcbbc6eebd569461b619aee064f688f964020d19d4624d6f4455bf242a7fdc3` |
| 84001 | closed | [5,6] | ABSTAIN_NOT_LOCALIZED | `9aec6c933d196499d6a0265199e0ab5268ddb666bf1f33c0cd869c7f89e82a5a` |
| 84002 | closed | [5,6] | ABSTAIN_NOT_LOCALIZED | `a4813372e241e7ce4884ae9815a8974d13e2c700df6ae8f97121841d7737f7dc` |
| 84003 | closed | [5,6] | ABSTAIN_NOT_LOCALIZED | `8d86ef8af9a434553d5d2b6093d1305429ab1e3069fa9856797a95876dad06af` |

**Scientific verdict:** passive four-turn sensing preserves observation consistency and deterministic replay but cannot identify original target cue on any of four exposed seeds. This is not proof a policy using exploration cannot succeed. No behavioral reward improvement, training, native Wingless/Yggdrasil integration, independent validation, or scientific first-use accepted.

## Required E-D146 observation-guided navigation candidate, without hidden state

1. Input strictly `env.reset()` / `env.step(action)` official `image`, `direction`, `mission`, scalar reward and termination. Prohibit `env.unwrapped`, `grid`, `agent_pos`, `success_pos`, `failure_pos`, internal RNG, direct map or training on held-out seeds.
2. Build a tiny deterministic agent-state machine from observation-detected walls, traversable free space and object positions. Only sensor-based movement and turn commands. Record actions, observations, perceived pose transitions, and explicit uncertainty; no world-coordinate oracle.
3. Explore to find **which** object is the isolated original cue. If visible evidence cannot disambiguate, abstain rather than assign ground truth; always count abstentions and action budget.
4. Once acquired, retain object type and visit decision junction using identical movement controller for retention/no-retention ablation. Match episode seeds, interaction exposure, per-seed budgets, and implementation environment. Log success, reward, action count, abstention, CPU and peak memory.
5. Use only the already-exposed four seeds in engineering exploration, then prospective FIT/VAL/DEV only under qualified frozen protocol; DO NOT consume sealed HOLDOUT without independent scientific first-use acceptance.
6. Require actual end-to-end reward superiority and retained ability under cold restart, plus fair trained conventional controls, before any scientific claim or model-selection ingestion.

**Scope:** research PR only; no FORGE production autonomy, controller, queue, training, acceptance or promotion modification.
