# AC-04 — Source-free Linux/Windows benchmark qualification

**Status:** DRAFT / SOURCE-PINNED / ORIGINAL SCIENCE NOT AUTHORIZED

## Purpose and ancestry

This work is **not** an admitted ITD-02 original experiment, scientific-first-use, F139 work item, controller, scheduler, accepted scientific reference, or native Wingless/Yggdrasil model change.

Parent AC-03 draft: [PR #1057](https://github.com/spoonman136668-ai/FORGE/pull/1057), exact head `45639966ff8b868acf791159f931408abc7ecc64`. It stacks on AC-02 [#1055](https://github.com/spoonman136668-ai/FORGE/pull/1055) and AC-01 [#1054](https://github.com/spoonman136668-ai/FORGE/pull/1054); none was merged at qualification setup. The existing [ITD-02 charter #857](https://github.com/spoonman136668-ai/FORGE/issues/857) retains all scientific and admission boundaries.

Original source `research/ac03_sourcefree/ac03_benchmark.py` SHA-256:
`b4295236b37b6b017841a863ab8fd551fee26cdafa8f5b02a4d80afdc78f2c5d`.

## Source-free qualification

A single, narrowly scoped **push/PR GitHub Actions workflow**, no cron, queue, dispatch API, long-lived controller or new scientific admission:
`.github/workflows/forge-ac04-sourcefree-crossos.yml`.

Only the exact AC-04 branch and requested stacked-PR base match. GitHub-hosted ubuntu-latest and windows-latest runners independently:

1. Verify the current repository SHA and that the frozen AC-03 source commit is an ancestor.
2. Run the existing AC-02 source-free tests and AC-03 source-free tests, plus new AC-04 exact source/counterexample/false-claim guards, Python 3.11 standard library only.
3. Run 11 representative workloads, three repetitions per baseline/candidate arm, in **independent short-lived Python processes**. Every arm uses the same generated source-visible workload and preserves expected output parity except explicitly approximate count-min sketches, whose collision overcounts must remain visible.
4. Record process CPU, wall time, Python-tracked allocation peaks, and process peak RSS where available. Windows process peak RSS remains **unavailable** because the pinned AC-03 child does not expose it on that platform. Null is the correct result; no invented memory values.
5. Store raw 66 per-OS sample records and summarized 11-case ratios as GitHub Actions artifacts with source SHA and run commit identity. Excluding Python process startup from internal time and using tracemalloc materially limits claims.
6. Preserve every losing variant and each known information-theory/hardware boundary; **all 36 candidate ideas remain under consideration**, but only 11 have a measured representative workload.

**Scientific validity:** no source-birth proof, independent original outcome source, sealed unknown-family evaluation, heldout access, native learning superiority, or first-use witness. All values are **development-only engineering evidence**, not qualified causal-transfer gains.

## Qualification incidents and their classification

First AC-04 run [#40779966616](https://github.com/spoonman136668-ai/FORGE/actions/runs/40779966616) stopped in setup-python because `cache: false` is unsupported by the used action. Source checkout and identity checks passed; benchmark was not reached. This is an **infrastructure/configuration failure**, not a scientific negative. The narrow workflow-only correction is commit `f618046d1901b865a430d8b6ab1a12d32dd10f27`. Retain the failed run as provenance.

**Actual fixed-commit Windows/Linux results:** verify from the workflow run and final artifact before recording PASS; do not infer success from this document.

## Next gate and authority

After the exact GitHub candidate jobs succeed, record the per-platform result identity and compare CPU/RSS/Python allocations with paired controls. Only after full frozen native qualification and one required full integration regression may eligible results proceed for separate scientific admission. The independent ITD-02 consequence source is still NOT_VERIFIED for this scope.

`AC04_SOURCE_ONLY=TRUE`
`AC04_ORIGINAL_SCIENCE=FALSE`
`AC04_GITHUB_WINDOWS_LINUX_QUALIFICATION=PENDING_VERIFICATION`
`F139_QUEUE_OR_POLICY_CHANGED=FALSE`
`NEW_CONTROLLER_OR_SCHEDULER=FALSE`
`PROTECTED_MAIN_OR_MODEL_MUTATED=FALSE`
`AC04_ACCEPTED_SCIENCE=FALSE`

## Windows checkout newline correction

The second run demonstrated Linux success and Windows test rejection solely at the raw checkout SHA-256 invariant: Windows checkout represented an unchanged Git blob with CRLF. The bounded repair pins both the original Git blob SHA and SHA-256 of `git show HEAD:research/ac03_sourcefree/ac03_benchmark.py` canonical committed bytes. It does not weaken source identity, modify AC-03 methods, rerun used science, or reinterpret missing Windows measurements as a scientific negative. Requalification against the corrected exact head is mandatory.

## Windows CPU timer limitation

The third run [#40780191248](https://github.com/spoonman136668-ai/FORGE/actions/runs/40780191248) passed both OS test sets and executed 66 isolated benchmark samples per OS. Linux source-only qualification/artifact succeeded. Windows output passed execution but failed a report-only assertion requiring every CPU ratio to be non-null. Its CPU timer can report a zero baseline for very short Python workloads. This is an **instrumentation limitation**, not a scientific negative or proof of CPU speedup. The bounded repair now reports `cpu_ratio_candidate_over_baseline=null` with `cpu_ratio_status=ZERO_BASELINE_TIMER_RESOLUTION` and preserves measured wall-clock ratios separately. No fabricated CPU ratios or missing memory measurements are permitted. Corrected cross-OS rerun still required.
