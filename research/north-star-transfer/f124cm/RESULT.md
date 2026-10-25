# F124CM — original-source causal expressivity falsification

**Completed 2026-10-25, development-only.** The original source experiment [F124-CL #617](https://github.com/spoonman136668-ai/FORGE/pull/617) already exposed all 24 internal E2/F2 development cases with **0/12 successful CB E2 causal-positive/hard-negative pairs** and **0/12 CB F2 pairs**. Do not replay, relabel, optimize against, or open the original protected 128-case cohorts. This new **mathematical source-law test** explains one *necessary architectural obstacle* for E2; it does not claim a newly trained learner or new source-world trial.

## Actual frozen evidence

- Exact preregistration BEFORE analysis implementation: `4cbbdfe785900e9edc875e7f1c1a4bc5da7beef3`, `FROZEN_PROTOCOL.json`.
- First code and original source-pinned analysis commit: `ebea655f4f365ac91b919d5d5bb9eceae4ef7458`.
- Original internally authored source law: `f124cj_internal_source.py`, Git blob `4e7bbd8f93dab1c7242a9374c75731302b034f31`.
- Original unmodified CB 32-bit learner: `f124cb_dual_link_learner.py`, Git blob `8a10bf8cec12afc7d8703e3586d8eba91ebfdc7c`.
- Original equally trained CC separate fitting objective, **SAME** 32-bit hypothesis class: `f124cc_trained_two_link_control.py`, Git blob `29c0c02f54ea539bed0910fe82adcc86d3aff94d`.
- Original hosted qualification **COMPLETED SUCCESS** at the exact analysis code head: [GitHub Actions #40236400928](https://github.com/spoonman136668-ai/FORGE/actions/runs/40236400928), Linux original job `121298814794` PASS, Windows original job `121298814949` PASS.
- Original full witness JSON hosted artifacts, no ChatGPT Library: Ubuntu `12615495755` ZIP digest `sha256:ef6a61fcb3164dc6b2b11cda947f623fb48f4ee2b6f9324356a5e990009d4718`; Windows `12614664571` ZIP digest `sha256:a974e21e2ce091e491460f4825219959445f541db94601e4491d118078d9dbe0`. ZIP digest is packaging, **not** the canonical science payload digest; the small JSON witness files have process-time-dependent metadata and are not byte-equality asserted.

## Mathematical finding (source-law exact, no private example)

Let the FOUR source-public input nibbles be `a,b,c,context`. Under every E2 `k0` and `salt`, define `a',b'` by swapping `a,b` iff `(context XOR salt)&1=1`. Original E2 output first nibble is

`u = (a' + ((5*c + 3*context + k0)&15))&15`.

`k1,k2` only affect other output nibbles, **not u**. For EACH `k0=0..15, salt=0..15`, the unmodified original source code on fixed, explicit non-private `{0,1,2,3}^4` public input subdomain witnessed a change in `u` when altering **each of the four input variables independently while holding the other three fixed**. The exact 256 parameter-pair ×4 coordinate = **1,024 verified concrete influence witnesses**, on each of Ubuntu and Windows; all passed. This is a full-domain *dependence existence proof* (a 4^4 subdomain counterexample suffices), NOT an exhaustive training or unknown-source scan.

By the exact unmodified CB algebra, `out[0]` has the form `affine(src[perm[0]])`, optionally XOR `affine(src[perm[1]])`. Therefore **NO CB 32-bit state, and NO CC state in the same exact frozen class, can make `out[0]` depend on more than TWO public input nibbles.** E2 `u` depends on FOUR, so **E2 is outside the entire CB/CC single-stage hypothesis class** regardless of FIT sample count, optimization search, threshold tuning, or train-only seed choice.

**Important logical limits:** This does not prove all source F2 cases are impossible, that generic binary composition cannot represent E2, or that a new native architecture improves unseen causal learning. In particular a **multi-stage combination of binary primitives can represent high-arity functions**; an additional causal intermediate, delayed state and/or flexible composition is a scientifically distinct direction, but MUST be learned and compared against fully trained conventional compositional/bayesian/recurrent controls on fresh authorized sources. No claim about native Wingless/Yggdrasil superiority, protected FSA approval, first-use, reward or transfer.

## Optimizer consequences and stop

**Actually used:** original content-addressed artifact reuse, frozen hypothesis-discrimination, a Pareto/expression-complexity lower bound for candidate architecture ranking. **Retained but not executed as trained optimizers in this mathematical falsifier:** Dream-RSI, ShinkaEvolve, ThetaEvolve, Promptbreeder, DGM, GenEnv. They remain eligible for bounded, genuinely distinct **train-only mechanism proposal** work—not to search more CB/CC parameters, choose holdouts, retune original F124-CL frozen thresholds or approve their own science.

**Stop rule:** NEVER rerun consumed `930000–930011` / `931000–931011` cases as prospective or relabel CB/CC failures. A new candidate must actually expand compositional expressive support, learn its parameters **from permitted experience**, pass no-memory and action-shuffled ablations, beat equally trained conventional sequence models and verify entire CPU/RSS/checkpoint/real-action costs. New original-world births remain under their separate authorized owner/FSA process, with preserved accepted refs and unknown-family protected holds.

`F124CM_E2_FOUR_PARENT_ORIGINAL_LAW=PROVED_IN_SCOPE`; `CB_CC_FROZEN_SINGLE_STAGE_EXPRESSIVITY=INADEQUATE_E2`; `NEW_NATIVELY_LEARNED_TRANSFER=NOT_DEMONSTRATED`; `ORIGINAL_NEW_FIRST_USE=0`; `FORGE_FSA_SCIENCE=DENIED`.
