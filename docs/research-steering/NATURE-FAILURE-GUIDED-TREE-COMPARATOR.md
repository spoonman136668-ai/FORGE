# Nature AI Scientist method → FORGE failure-guided tree comparator

**Status:** PROPOSED / SOURCE-ONLY / NONEXECUTING / SCIENTIFIC GAIN UNVERIFIED  
**Provenance anchor:** FORGE protected `main` `fe59428c7adb7a22f8fd9dc69d9426dec982067c`; isolated from open F139 recovery/cold-host PR #1875.  
**Primary external source:** Chris Lu et al., *Towards end-to-end automation of AI research*, *Nature* 651, 914–919 (published 2026-03-25), https://www.nature.com/articles/s41586-026-10265-5 .

## What the paper establishes — and does not

The AI Scientist uses hypothesis ideation, experiments, tree-based refinement and ablations; the template-free workflow progresses through initial implementation, tuning, research-agenda search and ablation. One of three manually selected AI-generated submissions cleared the reviewer-score threshold at an ICLR workshop with a 70% acceptance rate, and was withdrawn under the authors' protocol. This is evidence that some generated work can survive that workshop review, **not** proof of reliable original scientific discovery, continuous learning, or production-ready autonomous science. Naive hypotheses, incorrect implementations, citations and evaluation rigour are documented limitations.

**Do not port** the paper's manuscript/reviewer loop as an untrusted science judge, confuse LLM-generated papers with scientific progress, or assume an available paid model API.

## FORGE's observed comparator seam

- Existing finite source search: `f139/nci04_model_free_search.py` has **three** explicitly frozen development operators (within-context Laplace shrinkage; empirical standard-error abstention; cell-local exponential recency). It is bounded, semantic-deduplicated, history-preserving, and produces no science acceptance. `f139/test_nci04_model_free_search.py` tests deterministic exhaustion, negatives, source isolation and no provider calls.
- Existing advisory selector: `infogain/recommend.go` ranks frozen hypotheses by predicted information per compute and never dispatches or accepts scientific results; Dream-RSI/Pareto and other native optimizers are preexisting independent comparison families, not sources of delegated execution authority.
- **Gap:** finite enumeration cannot create a fourth genuinely new hypothesis after exhaustion. Merely rearranging or reissuing its three candidates is **not** a successful Nature-style autonomy mechanism.
- F139 recovery/owner custody is a separate engineering workstream. A successful Linux/Windows source test cannot substitute for owner-host acceptance or a scientific first-use claim.

## Falsifiable comparison

**H1 (candidate):** Given a truly **new, independently authenticated terminal negative or limitation** for a lane, a bounded failure-guided branch generator will produce and select more distinct, externally qualified *useful* hypotheses under equal total development budget than FORGE's strongest pre-frozen nonbranching control.

**H0:** No improvement under matched budgets and information, or improvement explained by more proposals, additional compute, source leakage, hindsight, or scoring bias. H0 remains viable until independently refuted.

**Unit of novelty:** (lane, exact parent source SHA/tree, canonical mechanism AST/structure digest, originating original terminal-event ID, original evidence digest). A rewrite, comment-only variant, source-repin, clock roll, new prompt, or old trial reused under a new identifier has **zero novelty**. Independently audited mechanism distinction is required for a claimed new idea; a new hash alone is insufficient.

**Proposed arms, same original evidence and budgets:**

1. **A — strongest existing control:** immutable finite enumeration + applicable existing frozen Dream-RSI/Pareto/infogain native policies, choosing the strongest **eligible** control on predeclared development data. Preserve each policy's actual constraints; do not combine or confer authority that the underlying components lack.
2. **B — branching without failure signal (ablation):** same permitted generator, branch depth and budgets, but train-only error categories masked. Tests whether any gain comes from branching alone.
3. **C — failure-guided branching (candidate):** bounded depth-2 generation conditioned **only** on newly verified training-side failure class, cause hypothesis and preexisting negative memory; no sealed holdout scores, retroactive error labels or protected owner credentials. Candidate children must contain a specific testable mechanism, counterfactual prediction, failure condition and intended ablation.
4. **D — no-history/negative-memory ablation:** **isolated DEV copy only**; keep true custodial negative history untouched. Tests whether memory, rather than pure search width, explains gains.

The brancher is not authorized to generate executable source in the owner process, propose arbitrary shell commands, modify live tasks, choose own scientific approval criteria or fall back to paid APIs. If no independent newly authenticated terminal event or permitted model-free generation exists, return `NO_NEW_HYPOTHESIS_SOURCE` with **zero** calls, writes, source promotion, or tests against protected scientific holdouts.

## Freeze before any real comparison

The scientific owner must independently preregister exact native source refs/checkpoint digests, source-birth disjointness, historical consumed records, lanes, seeds/splits, strongest fully trained control, evaluation domains, success thresholds, compute/cost budgets, stop rules and original-science first-use permissions. These are *proposed defaults*, not an authorization or adopted preregistration:

- Maximum **12 unique candidate evaluations per arm per lane**, max depth **2**, max **3** children per parent, max **4** newly verified terminal events; stop early on exhaustion. Do not backfill a nonexistent event or reallocate unspent first-use capacity.
- Same information available before each decision, same number of evaluated proposals, matched fresh-source access, code/data initialization, actions, total CPU/GPU time, RAM peak and inference/token costs. Log both successful and failed attempts; reject excess whole-process cost, not only fit-time cost.
- Separate development feedback from sealed unfamiliar transfer, cold retention/interference, action-consequence and intervention-value measurements. Freeze experiment order, sources and stopping decisions **before** results. Do not optimize on sealed results.
- **Proposed science threshold**: candidate exceeds the strongest eligible matched control in a prespecified primary useful-outcome metric by at least **10% relative** with a paired 95% confidence interval excluding zero, reproduces independently, and shows no retained familiar Brier deterioration beyond **+0.02**, no extra resource/authority budget, and no degraded safety. A zero denominator or too few independent examples gives INCONCLUSIVE, not infinite gain. Native scientific owners must approve or replace these thresholds **before** trial first-use; no post-result tuning.
- Primary useful-outcome metric must count *independently verified beneficial causal transfer/retention/intervention outcomes*, **not** draft quantity, number of branches, reviewer score, source-code differences, low-rigour proxy scores or CI completions. Novel distinct hypotheses, valid sources and costs are secondary diagnostic metrics.

## Qualification and custody gates

| Gate | What actually proves it | Current status |
| --- | --- | --- |
| Q0 source review | This document, exact source parent, no changes to execution surface | SPECIFICATION ONLY |
| Q1 engineering | Isolated pure source parser/selector, deterministic negative tests, deduplication, complete exact-head final regression on required platforms | NOT IMPLEMENTED / NOT RUN |
| Q2 training-only comparison | Replay on nonprotected, authorized development corpus; pre-frozen equal information/compute, negatives, ablations and fail-closed errors | NOT RUN |
| Q3 new-science use | Independently accepted original native sources, one-time claims, owner-authorized separate first-use and matched fully trained controls | NOT AUTHORIZED / NOT RUN |
| Q4 scientific conclusion | Independently reproduced prespecified causal/transfer gain over strongest control, retention/cost/safety gates | UNVERIFIED |
| Q5 runtime/deployment | Separate signed owner release, protected merge/cutover, original Windows SID/task/lock/SQLite custody and sustained real cycles | HOLD |

Expected negative controls: invalid/duplicate/semantic-replay source, relabeled old terminal, same event across two lanes, incomplete original chain, missing witness, absent new feedback, holdout leakage attempt, incomplete negative archive, resource overrun, ill-formed code, conflicting results, attempted protected mutation, ambiguous publication, loss of lock, disabled provider, failed source continuity, and an always-negative benchmark where branching **must not** discover a fictitious gain.

**Evidence required:** exact `repo/PR/SHA/tree`; original event and source/evidence identities; code/toolchain versions; every proposal and rejection; original trial consumption and full negative history; per-arm source access, cost, wall/CPU/GPU/RSS and models; predicted outcomes frozen before tests; source/holdout separation; test/run IDs; reproduction/independent-review decisions. Do not use an old acceptance receipt on a changed SHA. Distinguish ENGINEERING PASS, SCIENTIFIC PASS and DEPLOYMENT PASS.

## Next permitted implementation scope

Build an **isolated, pure advisory library + deterministic unit tests** that accepts frozen, independently *supplied* historical development events, rejects source/semantic duplicates, emits content-addressed research *plans* only, and returns explicit ineligibility without side effects. Reuse existing FORGE contracts instead of introducing a second controller, scheduler, queues, signed certificate path, credentials, provider network operations, new workflow, or scientific admission implementation. Run focused tests, adverse controls, then full exact-candidate Linux/Windows final regression; do not label these as scientific gain.

**Current conclusion:** the Nature mechanism is potentially testable against FORGE's fixed search, but this document records **no implemented branching engine, authorized scientific trial, verified discovery, deployment, or improved autonomy**.


## Source-only implementation checkpoint (2026-11-23)

The original Q1 status above describes the preregistered baseline. Follow-up draft
source now includes `f139/nature_failure_guided_comparator.py` and
`scripts/test_fsa_nature_failure_guided_comparator.py`. The library emits only
content-addressed, UNTESTED_ADVISORY_ONLY research plans. It does not integrate
with F139's controller, owner ledger, worker, scheduler, scientific admission
or protected refs. Its input event IDs and receipt hashes are opaque: the
separate original owner must independently validate receipt authenticity,
complete negative history and source/tree custody. No signed or authenticated
science claim can be inferred from a caller-supplied field.

Focused local isolated Python `python -m unittest -v
scripts.test_fsa_nature_failure_guided_comparator`: 7 tests PASS before repository
commit. The tests include event relabel/receipt replay, consumed semantic
recipes, malformed/holdout evidence, deterministic limits and zero I/O.
This is not exact-head whole-repository Linux/Windows/native F139 regression.
Until exact-candidate CI and independent owner qualification pass, Q1 remains
**PARTIAL / FULL REGRESSION UNVERIFIED**; Q2–Q5 remain NOT RUN/HOLD.
The recipe catalogue is deliberately finite and its structured hashes alone
cannot establish the paper's genuine-hypothesis-discovery thesis. Independent
semantic novelty review and a fair science comparison are still required.


## Follow-up engineering qualification and Q2 source evaluator (2026-11-23)

The previous Q1 PENDING language is historical. **Q1 original isolated planning
implementation engineering qualification PASS at exact candidate
`3b5221a8f2b464abb3f72131261421447c53280d`** under the existing
repository's Linux+Windows CI, F139 source regression, and development rehearsal:
- Public Linux/Windows run 45229156763 SUCCESS, including all seven
  `scripts/test_fsa_nature_failure_guided_comparator.py` tests on both OSes.
- F139 native Windows/source run 45229156715 SUCCESS.
- Linux/Windows development rehearsal run 45229156728 SUCCESS.
This is **source engineering PASS only**, not owner-host deployment, live
controller health, novel hypothesis discovery, source-authenticated scientific
outcomes or accepted first-use. Some unrelated steps are intentionally skipped
by the existing CI's source qualification profile; preserve run/job receipts.

Follow-up **Q2 evaluator source** now lives in
`scripts/nature_training_replay.py`, with adversarial tests at
`scripts/test_fsa_nature_training_replay.py`. It requires a preregistered
development-only source/tree/corpus identity; exactly four matched A/B/C/D
arms; preselected strongest-control family; identical event and information
identity; 2–12 equal paired cases; 5% total whole-process CPU/wall matching,
absolute resource caps; zero model calls/holdouts/first-use; explicit negative
controls and +0.02 retention-drift veto. It returns
`SOURCE_UNVERIFIED_DEV_DIAGNOSTIC` **even for favorable labels**. Its
input digests and declared outcomes are not independently authenticated by
the evaluator, and no original terminal data or paper experiment was imported.
Q2 actual matched empirical development comparison remains **NOT RUN** until
the original scientific owner supplies and verifies an eligible frozen corpus,
strongest controls, original negative chain and cost receipts.

The added Q2 evaluator and tests require a **fresh full exact-head final CI**
on the later source candidate; prior Q1 CI must not be reused as that proof.
Q3 new-science first-use and Q4 scientific gain remain NOT AUTHORIZED/UNVERIFIED.
Q5 deployment is HOLD. No new controller, schedule, API, workflow, owner task,
original SQLite, scientific checkpoint or accepted refs were touched.


## Q2 corpus and comparator capability audit (2026-11-23)

**Corpus gate: BLOCKED / NO ELIGIBLE ORIGINAL CORPUS READILY AVAILABLE IN THE TRACKED PUBLIC SOURCE.**
A bounded repository search found no independently authenticated, task-scoped
native terminal-negative cohort suitable for a matched four-arm scientific
comparison. Existing Native Discovery F1/F3 populations are explicitly
synthetic labels/history and are not authentic Wingless/Yggdrasil studies.
The small RSI-R4 repair-history cohort is historical software repairs, has
only two training exemplars and is explicitly inadequate for general task
performance or science-transfer claims. Do not relabel either corpus or reuse
F1/F3 synthetic labels as scientific event outcomes. The original F139 owner
ledger/runtime is not read or altered by this public source audit.

**Generator limitation: the current Nature-plan producer is still a finite
hand-authored recipe catalogue.** It selects at most three predefined
mechanism structures for three fixed failure classes. This is not an
unconstrained tree-search engine, adaptive hypothesis synthesis, or evidence
that a genuinely new mechanism can be invented after recipe exhaustion.
A distinct structured digest is a de-duplication key, not proof of semantic
novelty. The method's core scientific claim therefore remains untested; do not
advertise this catalogue as AI Scientist-equivalent autonomy.

**Evaluator provenance hardening:** Q2 rows now bind to four frozen,
distinct caller-declared source identities and fixed A/B/C/D arm roles.
This prevents accidental arm swapping and simple source aliasing. These
identities are still caller declarations, not authentication; a separate
original owner must independently verify the source bytes and original
terminal receipts. The new adverse test covers role/source mismatch.
Even favorable labels remain source-unverified development diagnostics.

Q2 actual empirical comparison remains **NOT RUN** pending an eligible,
complete, original development corpus and a materially genuine bounded
failure-guided generator. The next engineering experiment should test
prospective hypothesis synthesis/branch expansion using only independently
verified training-side negatives, against the strongest preselected control,
with blind-branch and negative-memory ablations. No holdout access, training
on sealed data, retroactive relabeling or first-use is authorized.

The prior native F139 source workflow was still in progress on ancestor
\`7e7829e741eb788be0b5bae5c78016ac8941b667\` at last read; do not reuse its
pending state as qualification for this new candidate. All full exact-head
regressions must run again on the latest commit. The previous full public
Linux/Windows run and development rehearsal passed on that ancestor only.
