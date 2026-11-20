# Research portfolio — north star and agent orientation

**As-of:** 2026-11-20  
**Audience:** New human or AI research contributors who need to understand the owner's direction, the distinct projects, what has actually been established, and what work is worth doing next.  
**Status:** Orientation and research intent only. Not a frozen experimental protocol, accepted scientific result, execution authorization, global controller contract, or a substitute for a project's AGENTS.md and native owner rules.

## In one minute

The long-term ambition is to create **persistent, cumulative, increasingly general native machine intelligence**, eventually capable of language, reasoning, planning, unfamiliar-world learning, and safeguarded self-improvement, without requiring a conventional transformer or autoregressive token-prediction model as the cognitive foundation. The systems should ideally learn and operate at substantially lower compute and memory cost than conventional approaches, but efficiency and broad intelligence must be measured, not assumed.

The owner is not trying merely to build a better chatbot wrapper, accumulate test passes, or automate GitHub issues. The goal is a working learner that discovers useful relationships, remembers how to use them, transfers them to unfamiliar circumstances, repairs damaged knowledge, and gets measurably better over time.

**A successful engineering implementation is not a scientific breakthrough.** We have functioning bounded mechanisms and reproducible tests. We do **not** yet have accepted proof of broad general intelligence, sustained autonomous recursive self-improvement, or a full native learner that improves continuously without loss of earlier abilities.

## The north star: what would constitute success?

A native system should, after real interaction with an environment:

1. **Acquire** grounded information and form native representations rather than rely on a hidden external model doing the thinking.
2. **Understand consequences** of actions and distinguish causal relationships from spurious correlations.
3. **Retain** previously useful abilities *functionally*, including across checkpoint saves and cold restarts. Preserved bytes alone do not prove retained competence.
4. **Transfer** learned relationships to genuinely unfamiliar worlds, causal mechanisms, compositions and tasks without leakage of withheld answers.
5. **Adapt and repair** selectively when predictions conflict with evidence, avoiding wholesale retraining and catastrophic interference.
6. **Accumulate** additional competence within explicit memory, compute, latency and energy budgets.
7. **Evaluate itself** by conducting or proposing informative interventions, comparing alternatives and retaining only independently demonstrated gains.
8. **Eventually support** native open-ended language, reasoning and useful autonomous behavior, not merely synthetic benchmark performance.

The central falsifiable question is: **Can one persistent learner learn a new causal rule, preserve old abilities, apply the new rule to an unfamiliar case, and beat the strongest appropriately matched conventional or symbolic control in measured quality and/or whole-process cost?**

Conventional models, teachers, externally licensed knowledge sources, symbols and language I/O may serve as *disclosed research inputs or controls*. They must not be silently substituted for the target system's own cognition. Never assume use of a donor's private weights, activations, or protected output as training material is authorized.

## Program map — independent owners, complementary roles

| Project / track | Purpose and distinctive architecture | Boundaries |
|---|---|---|
| **Yggdrasil** | Primary present priority for **one cumulative native causal learner**. Developmental/regenerative substrate, persistent learning, acquired causal knowledge, specialists, self-maintenance and bounded repair. Target is standalone non-transformer, non-token-centric general cognition. | The **Unified Causal Intelligence Amalgam** work is the sole designated *Yggdrasil integration coordinator*. Other Yggdrasil research chats/branches are independent contributors. No competing canonical learner, unqualified model promotion, checkpoint overwrite or research restart. |
| **Wingless** | Separate native, non-transformer, non-token-centric cognitive architecture. Researches raw-input-to-state learning, reasoning, language, compositional transfer, persistence and low-resource operation. | Never merge its cognitive foundation with Yggdrasil by assumption. Its current Go worker/broker is engineering infrastructure, **not** proof of native cognition. |
| **TTT-Hybrid Lab** | Independent research into state-space learning, attention, selective online/test-time adaptation, contradiction-gated updates, JEPA, persistent memory and conditional computation. The later owner-directed target is tokenless native cognition; some early reference implementations are **token-conditioned pilots** and do not yet meet that target. | Retain separate GPU/CPU qualification and experimental lineage. Neither an attention/SSM code path nor successful unit tests establishes transferable learning or tokenless cognition. |
| **FORGE** | Research operations and scientific improvement tooling: candidate generation, frozen experiments, provenance, comparison, recovery, and eventually bounded autonomy/Eureka-style improvement loops. | FORGE is **not** Yggdrasil's learner and is **not** a universal controller. It must not depend on CKB-plane. Public FORGE README presently describes a source-only prototype, not deployed/qualified live scientific execution. |
| **Mind-Palace** | Cross-agent, cross-chat **read-only advisory** durable context; project decisions, baselines, history, corrections and source pointers. | Not a controller, acceptance authority, or substitute for original source evidence. Pin a Git commit; validate remote bootstrap/catalog hash agreement; fetch bounded relevant index ranges; verify critical claims in originals. |
| **Mechanism Discovery / Mass Research / Weight Programming / JEPA / Energy / Topology** | Independently falsify candidate learning mechanisms: direct programmed weight structure, action-consequence discovery, active interventions, representation learning, self-assembling local graphs, predictive energy, memory repair and efficient optimization. | Contribute **findings and qualified code proposals**, not unreviewed replacements for accepted model weights or a second integration destination. |
| **CKB-plane, KTRADE, K Terminal** | Separate operational/control or application programs. They are not alternative owners of FORGE or Yggdrasil intelligence research. | Observe each repository's own authority, runtime and safety policies. No cross-system execution or trading authorization follows from this guide. |

### The Yggdrasil coordination rule

There is **one** designated coordinating workstream: **Unified Causal Intelligence Amalgam Work**. It coordinates the cumulative Yggdrasil learner and checkpoint lineage. Other Yggdrasil research efforts should independently test hypotheses, preserve failures, identify the exact native integration interface, and submit their evidence to the Yggdrasil repository. They must **not** self-promote into the accepted learner or replace ongoing cumulative state. This coordination rule is scoped to Yggdrasil; it does not make Yggdrasil or FORGE the authority over independent projects.

## Current evidence — do not confuse intention with achievement

**Engineering: PARTIAL PASS / many focused mechanisms work.** There are implemented source paths, reproducible isolated pilots and some cross-platform CI receipts. These demonstrate that specific code or tests work on their stated source, not that the broader system has learned intelligence.

**Science: MIXED, with important NEGATIVES.** November investigations found, among other boundaries:

- Yggdrasil specialist learning and saved state did **not** consistently preserve native familiar-task predictive quality. Functional-retention regression is a priority. See [Amalgam PR #1278](https://github.com/spoonman136668-ai/Yggdrasil/pull/1278) and [retention investigation PR #1329](https://github.com/spoonman136668-ai/Yggdrasil/pull/1329).
- Synthetic high-coverage knowledge work correctly handled familiar relationship families but did not demonstrate unfamiliar-family causal-rule discovery. More facts are **not** automatically more reasoning.
- JEPA components can learn narrow predictive relationships, but adding specialists or additional interaction capacity does not automatically improve native readout or retention; stronger controls often tie or outperform them. See [JEPA limits PR #1326](https://github.com/spoonman136668-ai/Yggdrasil/pull/1326).
- Some causal discovery failures came from **non-identifying observations**. Choosing discriminating interventions may matter more than passively collecting more examples.
- Direct weight programming produced bounded constructed successes, not proven broad general intelligence or superiority over fully fitted controls. See [WSP development PR #1344](https://github.com/spoonman136668-ai/Yggdrasil/pull/1344).
- Adaptive topology and energy-based inference can work in constrained cases, but their extra machinery did not establish superior effectiveness or whole-process efficiency over simple strong baselines. See [topology PR #1340](https://github.com/spoonman136668-ai/Yggdrasil/pull/1340).
- A memory/retrieval pipeline can preserve references while still missing the necessary evidence for an accurate answer. Source coverage and **measured answer improvement** matter more than counting stored records.

**Deployment and autonomous improvement: UNVERIFIED unless separately proven by the relevant native owner.** Neither PR existence, a successful workflow, an intact checkpoint archive, nor an automated proposal loop proves a deployed learning system or scientific self-improvement.

**Source-specific status check at writing (2026-11-20):** Yggdrasil [Amalgam PR #1278](https://github.com/spoonman136668-ai/Yggdrasil/pull/1278) is **open/draft**; [LINEAGE01 PR #1322](https://github.com/spoonman136668-ai/Yggdrasil/pull/1322) is **open/draft** and reports focused archived-source/cross-platform qualification. These are not accepted model integration or independent scientific superiority. Future agents must refresh PR, branch, SHA, CI and owner state before making current claims.

## Highest-value research sequence

1. **Establish a genuinely native knowledge base.** Ground relationships in permitted source observations, with provenance and versioned state. Do not call a hand-populated graph or programmed circuit learned cognition.
2. **Prove functional retention before expansion.** Freeze old capabilities, learn new ones, cold-restore the checkpoint, then test both old and new abilities. Record all regressions and interference.
3. **Discover unfamiliar causal rules through useful actions.** Present competing hypotheses and let the learner choose interventions that distinguish them. Compare against matched random-action, information-gain, symbolic and fully trained conventional controls.
4. **Repair without global erasure.** Test contradiction-triggered bounded adaptation, frozen rollback, local structural repair and rehearsal, with matched compute and old-skill controls.
5. **Measure generalization and total cost.** Hold out entire mechanism families or unfamiliar environments; evaluate long sequences, action-consequence learning, retention, transfer, sample efficiency, wall clock, peak memory and energy when measurable.
6. **Integrate only qualified gains.** A useful independent finding becomes a proposed native integration at its proper project interface, not an automatically promoted checkpoint. Keep Yggdrasil's one cumulative learner and preserve other projects' isolation.
7. **Then pursue self-improvement.** An autonomous cycle must propose, test, reject/revert negatives, retain replicated benefits and improve subsequent outcomes. Automation throughput alone is not RSI.

For each prospective test: **freeze the hypothesis, thresholds, seeds, splits, permitted information/actions, fully trained strongest controls, compute/latency budgets, ablations, negative controls, stop rules, checkpoint and data provenance before first-use**. Do not tune against withheld outcomes. Engineering PASS and independent SCIENTIFIC_PASS are separate verdicts.

## Agent operating contract

- First read **the local repository's AGENTS.md and source-of-truth research charter**. Verify current main, exact branch/head/tree/SHA, open PRs, prior work, CI, frozen test identity, owners and authorized runner. Do not duplicate PRs or consumed trials.
- **Do not invent current status** from a chat, an old recap, an unmerged PR or cached Mind-Palace memory. Preserve provenance links and distinguish historical, reported, source-verified and independently qualified evidence.
- Keep **ENGINEERING / SCIENTIFIC / DEPLOYMENT** reporting separate, using PASS / FAIL / UNVERIFIED, plain-language meaning, measured gain or negative, exact source/run, uncertainty, and whether the owner must act.
- A test or publication is **not** itself authority to execute workers, create competing controllers, alter canonical checkpoints, mutate accepted refs, run first-use experiments, deploy, trade, or merge. Use the actual scoped owner and accepted process.
- Reuse prior qualified work; make the smallest compatible change. For an authorized candidate, use focused checks and negatives, then its required full final regression on the **final** SHA/platforms, with source and custody receipts. CI success is not scientific acceptance.
- Preserve **all negative findings** and abandoned hypotheses; they prevent future repetition and overclaiming. Never relabel a failed frozen experiment as a success because a new patch passes.
- Avoid paid APIs, unauthorized scheduled automation, indiscriminate runner use, hidden model inference, leaked secrets or unrelated cross-repo changes.
- Agent deliverables should live in the relevant **repository** with a readable synopsis, a reproducible evidence trail, source refs and the exact native integration interface. Do not treat a chat artifact as durable implementation or acceptance.

## Read these before claiming progress

- [FORGE scope, boundaries and status](https://github.com/spoonman136668-ai/FORGE/blob/56feee68a02add2a6cc75529496d1ab3d9643225/README.md)
- [FORGE agent isolation rules](https://github.com/spoonman136668-ai/FORGE/blob/56feee68a02add2a6cc75529496d1ab3d9643225/AGENTS.md)
- [Yggdrasil north-star charter](https://github.com/spoonman136668-ai/Yggdrasil/blob/5e74f8db85b2f5839c42148c0dfba69a88b1a2c9/research/architecture/yggdrasil-north-star.ice)
- [Yggdrasil cumulative Amalgam work](https://github.com/spoonman136668-ai/Yggdrasil/pull/1278)
- [Yggdrasil checkpoint-lineage work](https://github.com/spoonman136668-ai/Yggdrasil/pull/1322)
- [Wingless standing cognitive north star](https://github.com/spoonman136668-ai/Wingless/blob/9a92fcae40c811c724b4214da03fff34126f6b4f/docs/architecture.md)
- [TTT-Hybrid reference scope](https://github.com/spoonman136668-ai/TTT-Hybrid-Lab/blob/main/README.md)
- [Mind-Palace direct retrieval/bootstrap contract](https://github.com/spoonman136668-ai/Mind-Palace/blob/1a399c0a73127826b98f3d2a6a4c33f8a5879343/CHATGPT_BOOTSTRAP.md)

**One-line handoff to another agent:** *Help build independent native, low-compute, tokenless cognitive systems that learn causal relationships cumulatively; prioritize Yggdrasil's single persistent learner and functional retention, preserve Wingless/Hybrid isolation, prove unfamiliar transfer against strong controls, treat FORGE as scoped research infrastructure and Mind-Palace as read-only context, and never confuse working code with demonstrated intelligence.*
