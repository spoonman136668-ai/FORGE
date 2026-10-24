# K5C-S0 — pinned original-source suitability and memory-necessity witness

**Status:** Original-source CODE audit + wholly source-free mathematical witness. NOT an original POPGym run, a native learner, a trained candidate, a scientific first use, or an FSA permit.

## Exact public source

- `proroklab/popgym` at commit `410d5aa626dae8024f498354d8781a0d1870c399`.
- `popgym/envs/concentration.py` exact Git blob `8f0d2d316c1ae63a7965ce1c56295a9aa403bbb9`.
- `popgym/core/deck.py` exact Git blob `12bcabfa9a96fd1261809ef0a446c74d3f3bfa86`.
- `popgym/core/observability.py` exact Git blob `72b5266f79a74b49140f603b859d59d19122b33c`.
- Source defaults `ConcentrationHard` to one deck, rank matching. The action space is 52 positions, observation is a 52-value vector with a rank token (0–12) at revealed positions and facedown sentinel 13 elsewhere. Source tracks a separate hidden shuffled deck `state` accessible through `get_state`: NEVER pass state, deck, full-info observability wrappers or privileged seed to a learner. The source explicitly marks `obs_requires_prev_action=True`; candidate must have access to its own previously chosen action.
- Original `step` supplies the current public observation before it hides an unsuccessful pair and its public reward/terminal/truncated flags. `info={}`. Standard partial observability is essential. A subsequent first flip hides the old unsuccessful pair again; remembering mismatches therefore matters.

## New falsifiable feasibility witness

Two different legal shuffled 52-card arrangements contain exactly four cards of each of 13 ranks. In both, the same agent actions `[0,1,2]` first expose two nonmatching ranks and then expose one rank-0 card at position 2. In one world the known rank-0 match is at position 0; in the other it is at position 1. The final public observation and latest action are **identical** in the two worlds, yet every possible next second-card action succeeds in at most one world. With the two world assignments equiprobable, a policy with no memory of previous observations cannot have greater than 50% immediate matching probability; a policy retaining the prior public observations chooses 0 in world A and 1 in world B and matches both. This is source-geometry/observation sufficiency only, not a measured learning advantage.

The source-free Python module has seven tests validating exact rank multiplicity, legal no-match history, observation alias, action-set disjointness, positive history dependence and zero protected first-use. No POPGym imports, seeds, resets, steps, reward-derived updates, native source edits, or K5B original cohorts occur.

Run: `python -B -m unittest discover -s . -p 'k5c_source_feasibility.py' -v` and `python -B k5c_source_feasibility.py`.

## Owner-only prospective original science

Source-owner freeze required *before* any public POPGym episode. Aim at **learned associative position→identity memory under distractor flips, controlled forgetting, and changing card positions**, not cue equality prewired as an oracle. Challenge fully trained exact-public-history associative lookup, trained recurrent/state-space and replay/consolidation competitors, and memoryless/current-only, shuffled-history and capacity-ablation controls. Same legal action histories and original physical reward budget; exclude `state`, `get_state`, `Deck.idx`, hidden arrays, full-observation/privileged `info`. Preserve complete chosen actions/observations/rewards, source lineage, cold-checkpoint/episode resets, CPU/memory/state size and per-method inference costs. Do not intentionally handicap exact-memory conventional competitors. Source family splits must be fully prospective and owner-controlled; fixed shuffled ranks alone need not support cross-family generalization. Stop if no native gain over equal-information strong fitted controls, or if quality gain costs more than justified. The official K5B MemoryEnv results, native R4 equivalence, Q21 frozen cohorts and FSA first-use restriction remain unchanged.

**Not run:** original POPGym, future FIT/CHECK/DEV, new native R5, protected scientific first use, FORGE F139/CKB/FSA queues, original research owner PR, protected merge, paid API.
