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


## Research operating portfolio — verified November 20, 2026 snapshot

This is an **operator-facing priority index**, not another canonical tracker, approval
queue or automatic integration route. The project PRs and issues linked here
remain the authoritative evidence. Statuses are a point-in-time snapshot,
not claims that training is currently running. Preserve independent experiments
and their negative findings when the chat that initiated them is archived.

**Primary operational blocker:** [FORGE owner issue #1830](https://github.com/spoonman136668-ai/FORGE/issues/1830)
and original [owner policy #807](https://github.com/spoonman136668-ai/FORGE/issues/807).
At authenticated [read-only owner run #44741726707](https://github.com/spoonman136668-ai/FORGE/actions/runs/44741726707),
the genuine Windows F139 task was **Running**, installed source
`c06403c8b6035c6c7013866a7ea08cef1244b507`, historical event
**1864** intact, versus protected `main`
`ece9ac168377c32d7a7cd4b694a57cc99dd0314d`.
The current 30-entry log tail had **28**
`MODEL_FREE_SEARCH_BLOCKED_FAIL_CLOSED/UNCLASSIFIED_VALUE_ERROR`
and **one** `UNCLASSIFIED_F139_ERROR`; selected authenticated
candidate count **0**. The contemporary V9 read-only portion
**PASS**, but its subsequent historical V41-only source pin is obsolete
and fails the overall workflow. Generic ValueError is not a proven
backend root cause; distinct GitHub API 403 rate-limit diagnostics
do not establish causality for all blocked entries.

| Owner / research track | Frozen question or mechanism | Current source / evidence | Scientific or operational status | Next qualified work / interface |
| --- | --- | --- | --- | --- |
| **FORGE F139 owner** | One original controller, authenticated issue intake, one worker, durable terminal outcome and restart | [#807](https://github.com/spoonman136668-ai/FORGE/issues/807), [#1830](https://github.com/spoonman136668-ai/FORGE/issues/1830), [read-only #44741726707](https://github.com/spoonman136668-ai/FORGE/actions/runs/44741726707) | **BLOCKED**: original alive but source differs from protected main; no new eligible candidate or worker advancement demonstrated | Diagnose actual model-free failure and establish independently authenticated source transition/worker admission. Do not replay existing tickets |
| **FORGE failure telemetry** | Safely count known model-free failures without leaking raw logs | [PR #1820](https://github.com/spoonman136668-ai/FORGE/pull/1820), merged at `ece9ac168377c32d7a7cd4b694a57cc99dd0314d` | **ENGINEERING COMPLETE**, original live backend failure still unknown | Reuse the existing V9 sanitized log rather than making a parallel diagnostic service; source-only module is not installed |
| **FORGE fresh development intake** | Single Yggdrasil READY candidate with cold custody, no replay | [PR #1844](https://github.com/spoonman136668-ai/FORGE/pull/1844), source head `9149d7bc1f94dbd67582b7f61e66d0507d91a40c` | **DRAFT / DISPATCH BLOCKED**; simulated READY is not real worker execution | Do not merge as proof of operations; requires independently authorized original owner release and the existing worker adapter |
| **FORGE research/training steering** | Compare manual and autonomous RESEARCH, TRAIN and self-improvement admissions | [PR #1818](https://github.com/spoonman136668-ai/FORGE/pull/1818), head `dae1e3846ad93deeb18c5e1df12a3a2fe27af9d0` | **DRAFT / SOURCE ONLY**; TRAIN adapter intentionally refuses execution | Reconcile onto qualified owner source only after one real development work path succeeds; no unqualified training mode |
| **FORGE → Yggdrasil CKAD** | Preserve exact learned checkpoint through staged cumulative update | [PR #1808](https://github.com/spoonman136668-ai/FORGE/pull/1808), head `22b6f61997f57244f8bb8413b6245f4fe527bf27` | **SCIENCE NOT PASS**: custody checks are not demonstrated transfer or retention; reported held answers 0/4 | Recheck producer-source lineage, matched fully trained controls and cold retention before scientific first-use |
| **Yggdrasil sole Amalgam owner** | One cumulative native learner, trained specialist and checkpoint continuation, without duplicating canonical state | [Amalgam PR #1278](https://github.com/spoonman136668-ai/Yggdrasil/pull/1278) at `86264b41a08d49f558418c0fba367f3a2636befa`; [lineage #1322](https://github.com/spoonman136668-ai/Yggdrasil/pull/1322) at `6ab65282c3bd85ef1fd9571287aa88404a62d791`; [retention #1329](https://github.com/spoonman136668-ai/Yggdrasil/pull/1329) at `f6c92619ff985dd78a324884b6765d1ca1702205` | **DRAFT / NO ACCEPTED CUMULATIVE SCIENCE RESULT** established here | Only the existing Amalgam integration owner can admit qualified learned state. Test old-skill retention, causal gain, unfamiliar transfer and cold reload |
| **Wingless independent native learning** | Reward-aware versus least-sampled exploration at matched public actions, information and compute | [PR #416](https://github.com/spoonman136668-ai/Wingless/pull/416), head `ea772824f4462257782fc866a770b5f397bd142e`; original [FORGE intake issue #1065](https://github.com/spoonman136668-ai/FORGE/issues/1065) | **DEVELOPMENT DRAFT**, already has a historical Forge feed issue; never reissue it blindly | Independently qualify matched controls, native retention and unfamiliar transfer; keep Wingless accepted ownership |
| **TTT-Hybrid independent causal probing** | Information-targeted causal probing versus random/existing controls | [R115 PR #311](https://github.com/spoonman136668-ai/TTT-Hybrid-Lab/pull/311), head `89adbdb916b9fb21ab4e383cfd2577eaf12f9d77`; [R113 #309](https://github.com/spoonman136668-ai/TTT-Hybrid-Lab/pull/309), head `2910f2974da86bcd74c1b3411784d821b1d002f9` | **PRESERVE NEGATIVES**: R115 reports feedback-benefit NO-GO; R113 cross-platform score parity FAIL | Hold promotion; isolate repeatability and comparator effects on its project-owned GPU lane |

**Consolidation rule:** An independent contributor should link a source-pinned
experiment and falsifiable comparison in the **owning repository**, not
create another chat-owned training owner. Reuse existing PR/issue identities.
Keep rejected or incomplete experiments visible and distinguish CI from
scientific qualification. The single FORGE owner may coordinate *eligible
engineering research*, never appropriate another project's accepted learner.

**Required operational proof before claiming FORGE is productive:** an
authenticated **new** issue or qualified candidate, deterministic source and
history selection, permitted existing-worker execution, independent terminal
receipt, crash/cold recovery, and next-ticket progression **without** resetting
historic work. Only after that, run a frozen Yggdrasil cumulative learning
comparison with controls, retention and transfer tests. At this snapshot
those proofs are **UNVERIFIED**.
