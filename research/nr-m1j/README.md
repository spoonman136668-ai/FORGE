# NR-M1J — source-free decision-discrimination screen

**Status:** ISOLATED DEVELOPMENT TOOL, not science. No original environment used, no FSA admission, no source cohort consumption, no Wingless/Yggdrasil native model mutation, no release/runtime/controller/queue changes.

## Purpose

NR-M1E (draft FORGE PR #1234, qualified exact head `dc4f19d4c3790db8deb89578f2c7a30215414f7d`) learned retention weights but did not select actual downstream actions or establish decision improvement. This NR-M1J gate tests the **smallest falsifiable engineering prerequisite**: can its existing frozen two-event memory change a public-action recommendation compared with two-slot FIFO and seeded reservoir histories under the same already-observed public transitions?

The readout is intentionally simple and held identical across arms: among previously observed legal actions, rank average signed public rewards, weighted by similarity between their preceding six-field public grids and the proposed next public state. No observed nonzero reward yields **abstention** rather than a fabricated action. No external environment reset/step is provided in this package.

## Inputs and isolation

- `PREREG.json` was committed first, at `e428cab143dfd70b78397c1b350c54dec119c611`, before `screen.go` and tests.
- Exactly one explicit role `SOURCE_FREE_ENGINEERING_ONLY`. This deliberately cannot admit the original frozen MiniGrid R8 source, protected CHECK/DEV/HELD, or arbitrary public source access.
- Caller supplies a previously completed-episode NR-M1E checkpoint, 3–128 already-observed public transitions, a source-public `NativePublicGrid` query and fixed reservoir seed. Neither input includes an oracle, next public consequence or correct action.
- Must have a trained/updated episode count, no open episode or unacknowledged terminal feedback. `Screen` **restores a private copy** of the candidate's checkpoint; does not mutate its source or its serialized identity.
- All events are validated through the existing strict NR-M1E six-field public-grid wire adapter. Terminal/truncated events are disallowed during preterminal action screening. Returned SHA-256 identities bind the input checkpoint and public history, without implying scientific first-use custody.
- Candidate, FIFO and reservoir store exactly two full public transition events. Their policy overheads differ: this is **not yet a matched physical memory/CPU comparator**. The candidate's retention coefficients, traces and RNG must be included in later resource accounts.

## Development checks

`screen_test.go` tests a deliberately **hand-weighted** candidate fixture against FIFO (to prove the screen detects an actionable disagreement, NOT to claim a trained win); repeatability and input immutability; total-reward-zero abstention; rejection of protected/unadmitted source roles, invalid public grid/rewards, terminal events, untrained/open-episode checkpoints, missing seed and overbudget histories; exactly equal two-event output memories.

These tests cannot establish reward or goal-completion superiority, causal discovery, cold-world retention or compositional/unfamiliar transfer. No claim of native learned action policy is made: the comparator readout is a source-free heuristic, not the Wingless `ChooseRewardExplore` implementation.

## Decision and next gate

**NR-M1J PASS**, if actually qualified, means only that a deterministic, controlled candidate-vs-baseline action-disagreement screen is available. A disagreement is not a win; same actions everywhere may indicate saturation and should block an expensive source experiment.

**NR-M1K admission prerequisites:** independently authorized new public-source cohorts, frozen source/roles/budgets/model identities, native integration authorization and real chosen action feedback, enough independent seeds, fully trained Bayesian/model-based/recurrent competitors with comparable public observations, actions and resource costs, cold state retention and unfamiliar causal transfer. Original MiniGrid R8 FIT/CHECK/DEV is not made reusable by this draft. FORGE's existing controller/FSA remains the only eligible science authority.

The next scientific result must derive from **real source-owned action/consequence differences**, not these handcrafted tests or counterfactual assumptions about unmatched actions.
