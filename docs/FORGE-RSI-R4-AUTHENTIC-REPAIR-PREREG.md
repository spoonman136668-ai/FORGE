# RSI-R4 — frozen authentic FORGE repair-history development cohort

**Status: preregistered source-only DEVELOPMENT, not sealed scientific first-use.**
Protocol source parent: cf727267007d0637abd8d8cd98a0fbbbd37f2752 (FORGE protected main, 2026-11-07).
Tracker: FORGE issue #1550. This document MUST precede all new R4 source/scoring code and any R4 measured outcome.
The historical fixes below were publicly known before this freeze: no scientific holdout novelty or autonomous RSI can be claimed from them.

## Frozen historical source task identifiers
Each row represents a *real previously merged FORGE repair*; data inputs are EXACT Git blob identities of the complete before and after source file at the recorded PR base/head commits, not assistant-written fixtures. No historical results are withheld from humans, and historic after-source is a reference only, never a source-generation or training-time oracle for holdout tasks.

| PR | Group | Path | Base commit | Head commit | Before Git blob | After Git blob |
|---|---|---|---|---|---|---|
| 1434 | train | f139/nci04_prompt_program.py | 259cd6f2e26a655ec1c2d6150482e85806c70b00 | 27c5fcdb0a53e1ea96a2e53c419a1a18fa688e1c | 253a2c4ec692f6d6d7ce7d60bd453795a3a502b7 | 9773d30a66338014420550edfd7cb1ba4c2b9cca |
| 1508 | train | f139/nci04_prompt_program.py | 860825eda4790f89f9b54c9100216af1322fc557 | c4ea247de49b655675f89166d783fb816943047c | 8781f3226ce3fed9e80f0c68bc845fe0639a2d2f | 643214ee8a581a4268bbd5bc8563d82e40c1ce9c |
| 1517 | validation | f139/nci04_v32_original_owner_transition_cli.py | 6988f1ebfe53fe54b13c5decbd58246b74ac2ad7 | 3d8478427b9182c49b6931fa69043753ed7b2d5a | dc597064fa83c1b996b2541c92c51ae342aa705d | 569ad130d0421df95f270ee7575985bff39a623d |
| 1525 | historic_holdout | nativefirstuse/f74_live_native_intake.py | ceb5f69097848992fa476d43054dea9120bd3696 | 61086e05e38b43c48cea6eb82826659c6afe48a4 | d58ce0ee847acf2e40d3ba509a37887e43007622 | f3ccf502ef1f7a4a87972485a780e3e9d225d658 |
| 1334 | historic_holdout | f139/local_controller.py | 80ae30719bcd9f179da4aa4e8f14dc36fd15818e | cf4ab24e3f95f37e2e79860edd1c99ee00290bf3 | bbaacc407fa4590e111fa19a395c62b2ddeccc86 | 90fa3b593b3ff7b6c9110118ba06d865d902a42a |
| 1543 | format_negative | nativediscovery/f2_world.go | 9527029d93aef61fc54f09c054fde9cd98f4f043 | fdf584ca1a83d50505062a118c6bdd67bd5504e6 | 7aea7bbf2896c4ecbdf3b027dcf3f1f78b3b992b | 2d3cc4bfb673e032ae6d7b40df77f0e7bf067b22 |

The two prompt-program fixes are in one TRAIN source-family group: NEVER split one changing module across training and holdout. The sole Go negative is a historically real whitespace hygiene fix, NOT a novel learning/repair improvement. The other historical cases are distinct source modules and historical code patches, but are NOT a representative task population. These are development exemplars to establish provenance, baseline behavior and repaired-source acceptance checks, not an adequate sample to prove a >=10% speed/quality gain.

## Execution and scientific boundaries

- Only original FORGE repository, exact pinned Git source bytes, no CKB-plane runtime, no model-generated or operator-provided arbitrary command, no paid API or agents. Source-only read and validation; no issue dispatch, source promotion, accepted refs, original-owner activation or Wingless/Yggdrasil edits.
- Separate original BEFORE and AFTER references and independent test/test-failure evidence. A candidate generated from historical AFTER bytes, merely replaying an existing fix, or reporting raw byte changes as semantic improvement is invalid. Preserve all failed and semantic-duplicate proposals.
- A separate future prospectively sourced task family with disjoint unseen source birth and precommitted evaluation is MANDATORY for any RSI_R3_PROVEN or scientific transfer claim; this historic cohort is *not* sufficient, regardless of green CI.
- On genuine fresh tasks compare unchanged FORGE, competent conventional repair, and strongest fixed/greedy source search at equal observations, actions, capacity and whole-process CPU/wall/memory/qualification budgets. Limit at most 16 new candidate sources per generation, two generations, without safety/test regressions; log every proposal, invalid, negative, and whole-process cost.
- Fixed pass condition from issue #1550 remains >=1.10x G1 vs strongest equal-budget baseline AND >=1.10x G2 vs G1 on independently unseen tasks, both Windows and Linux, valid full G1 and G2 source qualification and original owner's separately verified scoped authority. No post-result metric, data, cohort, budget or threshold editing to obtain PASS.
- The historical corpus validator may report manifest and source-authentication PASS; it MUST NEVER report task-solving PASS, an independent qualification, scientific-first-use PASS, deployed self-edit authority or RSI_PASS without separate genuine evidence.
