# E-D150 — Authenticated observation-reactive navigation results

Evidence: draft FORGE PR #1194, source commit `3d67c59d905e575b1fe022cab1195361918db060`, GitHub Actions [run 41141924400](https://github.com/spoonman136668-ai/FORGE/actions/runs/41141924400), Linux job `124359664902` **success**. Original Linux log emitted `PASS_ENGINEERING_OBSERVATION_NAVIGATION`, original MiniGrid MemoryS13Random-v0, **four previously exposed engineering seeds only**.

| seed | actions | reward | terminated | hash of action sequence |
| --- | ---: | ---: | --- | --- |
| 84000 | 3 | 0 | true | `4c750b999450a3a4963b08978f24316abd16517f7976804863d76bf1d24e51a7` |
| 84001 | 6 | 0.9936094674556213 | true | `8f85c4aae030695bbb387977012860633726713ddd30746070399eb3f1b10f82` |
| 84002 | 6 | 0 | true | `8f85c4aae030695bbb387977012860633726713ddd30746070399eb3f1b10f82` |
| 84003 | 4 | 0 | true | `ecd78bd35c0407c708c31de0fb6e34e6a91f52afef03dd3a80f15f4e997fe9ef` |

Mean actions 4.75. Positive-reward success 1/4 exposed seeds. Deterministic replay assertions passed. `first_unique_visible_type` was 5,5,5,6 respectively, but `initial_cue_identified` is **false in all cases**. The rule simply uses observed wall ahead to choose turn/move and has no cue-controlled decision, learning, retention, or demonstrated memory advantage. Thus the positive reward on 84001 is not evidence of acquired memory intelligence.

As of evidence retrieval, Windows job `124359665204` IN PROGRESS, full workflow not concluded. Scientific first-use NOT ACCEPTED. No native Wingless/Yggdrasil training or controller promotion. Next compare paired policies that actually differ only by retained original cue, after observation-derived localization; evaluate same exposed seeds with identical action and sensing budgets, log reward, action traces and abstentions, no holdout.
