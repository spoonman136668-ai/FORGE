# URC-R1 — two-chat research consolidation (advisory, no runtime mutation)

**Status:** DRAFT implementation/proposal, not deployed, not a new research controller.
**Verified starting FORGE `main`:** `49c7b15343bea3c201fb52b498d8c0f397384afe` (2026-10-30).
**Source:** `research/coordination/registry.v1.json`, `validate_registry.py`, `test_validate_registry.py`.
**First step:** `python research/coordination/validate_registry.py research/coordination/registry.v1.json`
**Tests:** `python -m unittest discover -s research/coordination -p 'test_*.py'`

## What changes

Unify **conversation-level coordination only** into two surfaces:
1. **FORGE Operations & Autonomy:** Existing F139/qualified project-controller state, release proof, qualified runners, research receipt custody, safe retries, authorized project-specific integration.
2. **Unified Research:** One prioritized hypothesis/experiment backlog spanning native Wingless and Yggdrasil, N Research, E Research, Replay Acceleration, computational acceleration, and supporting BIO/Optimizer/Mass/Language science.

The registry holds ten *advisory* research tracks. A `POINTER_ONLY` reference is not source-byte authentication. A `UNVERIFIED` scientific outcome is not an accepted finding. Existing Wingless/Yggdrasil architectures, their own source owners, frozen benchmarks, separate first-use rights, external controls, original native actor loops and qualification stay intact.

**Important non-duplication:** The existing `researchfeed.PreviewCandidates` and [RSH-01](../../docs/RSH-01-SIX-LANE-RESEARCH-EVIDENCE-PREVIEW.md) already provide a six-lane advisory evidence index. Do not introduce a replacement feed. The six canonical source lanes remain Wingless, Yggdrasil, BIO, Optimizer Work, Mass Research, Language Research. N/E/Replay/compute are *coordination tracks*, not newly accepted science-source lanes: their evidence must follow separately verified custodians and eligible original paths; do not pass them through RSH-01 by aliasing or waiving its source protections.

## Add an approach without adding a chat

Propose a new bounded track in the same registry with a unique id, scope, owner repository, source pointer (pointer-only), falsifiable next goal and `SEPARATE_ADVISORY` evidence route. The validator enforces source and authority boundaries. Before running anything, the actual experiment owner separately establishes immutable source SHA, rights and sample provenance, matched strong baselines, budget, preregistration, frozen holdout and stop conditions. This registry is not a submission, run ticket, PR merge permission, accepted ref, science result, or queue.

## Fast experiment funnel (existing owned runners only)

1. **Cheap source/math gate:** Test algorithmic capacity to alter useful decisions, absence of hidden ground truth, and focused correctness, using exact source IDs.
2. **Development real-world gate:** With existing authorization, test original selected observation/action/consequence and prospective matched control. Report *episodes vs actions*, returns and actual task success, replay CPU, peak memory and wall time separately.
3. **Retention/transfer gate:** Cold restart, interference, independent unseen causal families; no hindsight leakage or reusing exposed DEV as sealed evidence.
4. **Independent scientific gate:** Existing FSA/source-owner authority controls first use, immutable receipts, holdout and final regression; **no self-acceptance**. Proven candidate enters standard model-integration review.

Reject structurally invalid candidates early. Do not make negative science into infrastructure error, and do not skip any mandatory full regression or retune frozen thresholds. Cached tests are reusable only for exact matching semantic source, harness, dependency, toolchain, environment and provenance keys. Avoid paid APIs. Preserve independent native non-transformer and non-next-token design.

## Source/owner and chat-retirement gates (ALL UNVERIFIED at draft creation)

- **owner-continuity:** Independently authenticate original F139 Windows owner, release source/SID, chained ledger, V26 cutover outcome, multiple natural unattended ticks, and safe failure recovery. The posted owner issue comment is a *trigger*, not proof.
- **research-handoff:** Every active experiment and open draft has one actual custodian, source-pinned work-in-progress and recoverable next step. No active loop paused or chat-only commitment lost. Existing runners remain independent and qualified.
- **evidence-routing:** Demonstrate real result/evidence routing for **both** native source owners through existing qualified intake; no silent RSH-01 lane expansion.
- **unattended-cycles:** Witness repeated autonomous eligible work under the **existing** original controller, including a development negative and safe recovery, without duplicate dispatch.
- **science-and-owner-signoff:** Independent original-first-use custody, frozen thresholds/splits, full regression and non-promotion safety still pass, and the operator confirms no remaining chat-only responsibility.

The advisory validator **always** reports `retirement_ready=false` and refuses any hand-authored `PASS` in the metadata. Retirement readiness requires independent live readback, not editing a status field.

**Retire the extra chats only after all five evidence gates are externally witnessed.** Consolidation of new discussion can begin sooner; don't kill active research loops or remove chats that still own unique context until those obligations are transferred. Preserve archives, source pins, negatives and qualification receipts in their original authoritative repositories.

## Key operational limits

- This branch makes **no** runtime controller, executable work-queue, runner, repo protection, scientific authority, accepted model, scheduler, credentials, or protected-main changes. It **does** make a narrowly scoped existing **CI qualification workflow** change: both Linux and Windows run the pre-existing advisory Python registry validator and its tests, retaining all original gates and the latest protected-main Windows timeout (40 minutes). This is CI-source change, not new scientific or controller authority. Exact-head cross-platform CI must prove it.
- It grants no execution, automatic candidate selection, FSA/owner authority, first-use clearance, model promotion or standalone replay eligibility.
- `Mind-Palace` retrieval remains **read-only advisory** at one pinned SHA; `ckb-plane` is **not** the universal authority. Every program retains its own presently verified controller and independent approvals.
- Existing F139 source continuity is narrow: [continuity contract](../F139-SINGLE-OWNER-RESEARCH-SOURCE-CONTINUITY.md) lists only specific allowed read-only file paths. These new paths **are NOT covered**; future protected-main merge would require its ordinary qualified source transition. No merge from this draft without that exact compatibility and acceptance proof.

## Initial non-operational checkpoint

Snapshot: FORGE V26 PR #1251 merged and owner issue #807 has a V26 trigger comment. **On-host original cutover, natural autonomous cycles and scientific throughput are not verified here.** Wingless #438 and Yggdrasil #700 are unmerged native source drafts; Yggdrasil #704 is a source-public diagnostic proposal, not acceptance. We are not claiming the user can retire research chats yet.

**Measured goal (not a result):** at least 2x qualified experimental throughput at unchanged scientific assurance, separately measured from actual model learning-to-proficiency efficiency.

## H20 integration review — verified source boundaries, not a merge authorization

This checkpoint records the independently checked **engineering** boundary of the existing draft, not release approval. The completed [cross-platform qualification #41130107680](https://github.com/spoonman136668-ai/FORGE/actions/runs/41130107680) checked out GitHub's actual synthetic merge commit `9bea82699170ec6057d27417b6e1547ee4cc8a62`: coordination head `02d76274ca16a32ffcfc2c625b87284b098e4d80` merged into protected main `dd07f6477a722d1b3b20fa92fc1b764ff7c27470`. Both Linux and Windows succeeded. Their original F139 test suites each ran 1,442 tests (Linux 1 skipped, Windows 5 skipped); all 39 coordination Python cases and relevant Go suites passed. Both validators correctly returned `retirement_ready=false`.

The separately verified newer protected-main commit `1899ba6d98f14850e83f3db7ca4c6e7ef90ed6fb` is eight commits after that tested baseline. Exact `dd07f647..1899ba6d` compare lists **four additive F139 resource-accounting source/test files**, none of which intersects this PR's 12 changed paths. Exact common-parent comparison shows **only** `.github/workflows/qualify.yml` overlaps; main and research both preserve Windows 40-minute timeout, and the research branch adds three fail-closed coordination checks to the existing Linux and Windows F139 regression steps. GitHub currently reports the draft mergeable, but that is not final integration qualification.

The **last mandatory full regression must apply to the subsequently constructed exact current-main merge candidate**, not merely the tested `dd07f647` synthetic merge. The present H20 text-only advisory update intentionally triggers the pre-existing PR Linux/Windows qualification without invoking a new workflow/controller/runner or modifying F139 production source. Verify the new CI checkout's actual merge-commit parents/source identity before treating it as current-main integration evidence. Never transfer PASS across a changed source/merge tree without qualifying that tree.

**Release and retirement remain HOLD.** This draft has no independent formal PR review or protected-main integration authorization, adds paths outside the original F139 read-only source-continuity allowlist, and does not witness a second natural original-owner development cycle, active research handoff, independent science or user chat-retirement acceptance. Leave the PR draft/unmerged until those separate project-specific gates are properly satisfied. Neither GitHub mergeability nor H20 CI can grant scientific first-use, admission, execution, or promotion.
