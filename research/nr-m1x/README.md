# NR-M1X — Native delayed-credit falsification against a matched 32-step eligibility trace

**Classification: AUTHENTIC NATIVE IMPLEMENTATION TEST / SCIENTIFIC NO-GO.** This is an explicit source-free control test of real native Wingless and Yggdrasil implementations. It does not instantiate original Farama MiniGrid, demonstrate a real goal or evaluate off-policy actions.

## Frozen custody

Prospective falsification preregistration `PREREG.json` was committed **first** at `d464facb9aa6f2357e1b43a1ac5e78c469665159`, before either native test file. Exact unchanged native source:
- Wingless MG23 [draft #435](https://github.com/spoonman136668-ai/Wingless/pull/435), original `selected_target_credit.go` blob `4f33193cf0e90a82f515e1ab6996a8e707709b18` remains unchanged. Additive test `nr_m1x_eligibility_control_test.go`. Exact test head `4c41c7e86fb7c0e812d7d0eede2e300346e56bec`; original native [run #41036757156](https://github.com/spoonman136668-ai/Wingless/actions/runs/41036757156) **Linux PASS / Windows PASS**.
- Yggdrasil MG23 [draft #694](https://github.com/spoonman136668-ai/Yggdrasil/pull/694), original `selected_target_cells.py` blob `1b3f74f60d81145535c7e2d7dfeb71529f9d3d79` remains unchanged. Additive `test_nr_m1x_eligibility_control.py` and its inclusion in the existing original test workflow. Exact test head `2ae8324f35c004d944d846140b52e79775ffe62d`; original native [run #41036817053](https://github.com/spoonman136668-ai/Yggdrasil/actions/runs/41036817053) **Linux PASS / Windows PASS**.

## Controlled test: exact same source information

Both independent native selected-feedback APIs received 33 source-free abstract public-feedback events: one early forward action, **31 selected unchanged-public-view turn actions** with zero reward, and one terminal action with artificial positive reward. This is deliberately an **API stress fixture, not a physically possible MiniGrid goal trajectory**. The comparator is a conventional 32-decision rolling tabular eligibility trace that observes *only the same selected action, context, returned public state and terminal reward*. Upon positive terminal feedback, the newest action receives credit 32, next oldest 31, down to 1; actions outside the 32-step history receive zero.

Both native implementations returned exactly the conventional tally:

| Action in the abstract feedback fixture | Source-selected observations | Terminal credit, both native and conventional |
|---|---:|---:|
| 31 unchanged-view left turns (0), no local observed progress | 31 | **496** |
| Earlier forward action (2), outside 32-step trace | 1 | **0** |
| Terminal selected action (6) | 1 | **32** |

All `target` effect counters stayed at zero since no public target disappeared. Native action selector subsequently favors the heavily credited **zero-effect turn** in the fixture. An otherwise identical 33-event cohort with **no positive terminal feedback** had zero delayed credit for all actions. Cold snapshot/restore retained the native credited state; existing wrong/duplicate source custody tests also ran.

**Causal attribution negative:** these native MG23 layers implement a fixed history-credit heuristic, not learned identification of which preceding actions caused success. The equal-data conventional trace reproduces the outcome exactly for this source-only negative case. Since these fake source frames have no physical world semantics, this must **not** be reported as actual native goal regression or original navigation result. Real-world terminal associations could of course contain useful information, but native success is unproven.

## Stop decision and next distinct experiment

Do **not** promote these opt-in 32-step credit mechanisms as unique native delayed causal learning on the strength of source-only behavior, just as earlier N Research found Yggdrasil MG40 `Beta(1,1)` and Wingless DK17 `Dirichlet(1,1,62)` readouts equivalent to conventional controls. This result is separate from Yggdrasil's earlier V12 mixed/no-go reversal study [#594](https://github.com/spoonman136668-ai/Yggdrasil/pull/594) and Wingless T37 learned causal forecast/no-go [#323](https://github.com/spoonman136668-ai/Wingless/pull/323).

The next scientifically discriminating native learning mechanism must **learn action-conditioned multi-step predictive state/credit and distinguish meaningful consequences from arbitrary temporally adjacent actions**. Before consuming new authorized unfamiliar-world source, require a frozen **same-information, fully trained** eligibility TD/Q baseline, recurrent/state-space model and model-based planning control; show actual selected action differences, original goal return, heldout unfamiliar-world transfer, cold retention and whole-process CPU/RSS/checkpoint costs. Avoid reusing exposed DEV/CHECK/HELD as new first-use, or retuning consumed trials.

**Strict acceptance still separate:** Wingless original Windows ICE [run #41036765853](https://github.com/spoonman136668-ai/Wingless/actions/runs/41036765853) **FAIL** source-index freshness/typed relationships; Yggdrasil original G29 atlas [run #41036800464](https://github.com/spoonman136668-ai/Yggdrasil/actions/runs/41036800464) has source-index check failure. No waiver/bypass. The source-only cross-platform test passes do **not** qualify whole native PR or confer independent human review (Wingless issue #439 remains separate).

All three research branches are draft/unmerged, with zero original-world actions, no accepted model, no FORGE F139 automation, scheduler, research queue or first-use changes. Results preserved in `RESULT.json` and the cited original CI runs.
