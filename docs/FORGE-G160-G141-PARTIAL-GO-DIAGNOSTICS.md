# G160 — bounded partial Go diagnostics for original G141 timeouts

## Preimplementation source freeze
Protected-main parent `21b8649569bd9577c325da1ea99ecac81ff5df89`, tree `ddf7d95fe7883b0d12b700c9a19c89a87a1aaa6f`, branch `engineering/rar-g160-partial-go-diagnostics-20261109`. Exact five-file scope: `docs/FORGE-G160-G141-PARTIAL-GO-DIAGNOSTICS.md`, `scripts/check_rar_g141_parallel_go.py`, `scripts/check_rar_g145_pr_scope.py`, `scripts/check_rar_g148_go_cache.py`, `scripts/check_rar_g156_dynamic_base_cache.py`. No workflow, Go package/test, controller, researcher, owner, scheduler, acceptance, first-use or deployment change.

## Authentic defect
Eureka draft PR #1614 at exact SHA `59fadda0adad413a00920427c8d99feda7ffe34c` failed Linux G141 original first-attempt CI #42583135853 on November 9, 2026 with `G141_PARALLEL_GO_TIMEOUT`, while the same source's Windows native job passed. G141's temporary regular/race log files are deleted before failed-job output is printed; individual package progress is unavailable. Do not infer which science package or Go test is at fault.

## Correction and immutable controls
On monitored subprocess timeout, error or memory failure: kill the original process groups, snapshot both regular/race log files before the temp directory is deleted; print per-suite completed and pending package names, elapsed seconds, exit status and bounded 8 KiB tail, and retain the structured diagnostic in the original failure JSON. Always re-raise the original error. If diagnostic capture itself fails, mark it unavailable, never PASS. One synthetic incomplete-package negative control executes before real Go suites.

Preserve `MAX_SECONDS = 180`, shared v2 cgroup 4 GiB ceiling, all memory checks, exact source/tree and clean checkout, package parity, original `go test -count=1 ./...` and `go test -race -count=1 ./...`, Windows original test/vet/build, Linux vet/build and all F139/GenEnv checks; no test selection or retries. G145/G148/G156 admit only this frozen five-file source-pinned branch and do not admit ordinary harness edits.

## Acceptance and limitations
Require full original 8/8 first-attempt Linux/Windows CI and independent source-origin checks at exact candidate head before merge; fail closed if base/current main drifts, if race/regular tests are bypassed, or if any scope/negative controls weaken. A passing CI run validates compatibility and the synthetic negative control, **not** the real timeout-path evidence. Capture the two partial summaries and tails on the next naturally occurring failure rather than rerunning or modifying active Eureka research. This is an observability repair, not proven Go acceleration, learning or deployment.
