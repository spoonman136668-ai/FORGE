# RSI-R5 — frozen same-budget native proposal-selection impact check

**DEV ONLY, no scientific first-use or original-owner activation.** Frozen BEFORE implementation of the evaluator on 2026-11-07. Baseline FORGE protected main `3e83e0ddba0aedd397298a07ef53d1bc6bf301b3`; proposal-engine exact Git blob `7d5a1ebe8860f6ae69dff612cbe8fceb4d3d851c`; existing test fixture `f139/fixtures/model_free_yggdrasil_992ef.py` Git blob `f2fda603fbed965a3b4e7cc28844b2246bf8ac2b`. Original Yggdrasil proposals #838, #842, #843, #844, #846 supplied known, non-blind public-counter word programs, original historical control #845 a deliberately non-equivalent form. All historical identities already public, so this is NOT a novelty holdout and does not justify new science claims.

## Precise engineering question

After PR #1549 passed mandatory Linux/Windows full regression, does its source-only `public_success_count_order` guard actually reduce *provably redundant* candidate source proposals in original `build_plan` at unchanged 16-proposal budget? Compare exactly two **same-source** arms:

- **Control A (single-feature ablation):** run source on current protected-main code with `public_success_count_order` returning false only for the duration of `build_plan`. This is a faithfully isolated ablation of the new filter, **not** a separately installed previous binary, standalone optimizer or strong conventional repair baseline.
- **Candidate B (qualified):** run the unmodified `build_plan` using its source-authenticated symbolic certificate. Both arms consume identical original fixture bytes, historical `LEGACY` source identities, negative and consumed sets, fixed `history_sha256='a'*64`, fixed `mechanism_sha256='b'*64`, `eligible_parent_sha256=set()`, and `max_candidates=16`.

Frozen historical-history scenarios (source bytes reconstructed by the existing typed compiler from authentic original published programs):
1. `legacy_only`: original seven `LEGACY` sources, no added success-count history.
2. `p838_history`: same seven plus exact owner-produced PR #838 program source, **negative/unqualified parent**.
3. `p838_p843_history`: same seven plus PRs #838 and #843, both negatives/unqualified parents.

Run each scenario in independent Python processes in serial **A/B/B/A** on existing Linux and Windows qualification runners, no new workflow. For each process record source identity, resulting batch count/raw source hashes, count of exact provably success-count-equivalent candidates, process-local CPU, end-to-end process wall and per-process resource high-water RSS when OS exposes it (otherwise explicit UNVERIFIED). Compute two paired time ratios and median rather than cherry-picking. Keep **all** samples, failed/invalid outputs, original source derivation, final test verdict, and any NO_GO. The benchmark must be bounded (max 16 proposals per arm, 20 seconds per process) and entirely read-only. The original generated Python candidate is never executed in the installed owner.

### Predeclared development pass/NO_GO
- **Functional gate PASS:** B produces no source that the exact certificate proves equivalent to a consumed historical success-count program in scenarios 2 and 3; all arms preserve bound, distinct raw identities, original history and source-binding constraints.
- **Demonstrable efficiency improvement:** At least one of scenarios 2/3 has strictly fewer proven redundant proposals in B than in A, without reducing the total valid bounded proposal count or breaking full regression. Otherwise record `R5_DUPLICATE_SELECTION_NO_GO`, even when CI is green.
- Timing is exploratory and *not* a gate; require receipts on both OS and **do not label speedup** without paired whole-process reliable improvement. No adaptive retuning after observed result. No independent unseen source/task or tested accepted original-owner selection means **RSI_R3_PROVEN=false**, `SCIENTIFIC_PASS=false`.

No paid AI/agents, new queue/runner/controller/scheduler, original installed F139 owner, Wingless/Yggdrasil source changes, first-use admission, CKB-plane use, ref promotion or deployment. Future true engineering RSI remains bound to previously frozen two-generation >=1.10x G1 vs strongest baseline and >=1.10x G2 over G1 on unseen genuine tasks with qualified exact source and matched budgets.
