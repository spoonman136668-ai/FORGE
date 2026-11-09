# G162 — one exact-Eureka source Go race test-level profiler (DEV ONLY)

## Evidence and frozen source
- Main baseline `74c5804ada71bc28ce322aebcee31e1872e7158e` tree `3a1a964d73ffa0e606e69f3b89f5e6050ab5bb31`; development branch `engineering/rar-g162-eureka-race-profile-20261109`; exact 5 files: `docs/FORGE-G162-PINNED-NATIVEDISCOVERY-RACE-PROFILE.md`, `.github/workflows/qualify.yml`, `scripts/check_rar_g145_pr_scope.py`, `scripts/check_rar_g148_go_cache.py`, `scripts/check_rar_g156_dynamic_base_cache.py`.
- Research PR #1614 independent Eureka source `268b8c59561ec4063f0d8cb59b6e7fccb0d0069c`, tree `5cf15dee259190d52942d8c85d2136a5cd27bfbb`, never edited or rebased by this work.
- G141 original CI #42550112479 nativediscovery race 115.842s; #42584930022 race 118.626s; source `268b8c59561ec4063f0d8cb59b6e7fccb0d0069c` in CI #42586792360 timed out after 180s. Main source race about 1.2s. The two successful package receipts do not identify individual tests.

## One bounded, read-only diagnostic
- Insert a single DEV-only Linux postqualification step in the **existing** full regression workflow, after original Go regular/race/vet/build and isolation have already PASSed. Fetch one exact Eureka source Git SHA into a detached read-only worktree under RUNNER_TEMP (never research branch mutation), check exact SHA/tree/status and run once: `go test -race -count=1 -json ./nativediscovery`.
- Match original race arm GOFLAGS=-p=4, GOMAXPROCS=2, GOMEMLIMIT=1536MiB, Go 1.23.12; use GOTOOLCHAIN=local. The focused run is serial, not concurrent with regular Go, so it supports per-test attribution but does not establish a matched whole-job speed gain.
- Parse source-bound Go test pass/fail events: require at least 30 passes plus package PASS, emit top 25 test durations and original go-test outcome. Save bounded results and source event JSON for seven days. Never treat failed test as success. Only existing previously-run synthetic DEV tests are exercised; no independent scientific first-use.
- Add exact five-file branch-only frozen harness admission in G145/G148/G156. Original source controls, all original tests, negative controls, timing/memory limits, Windows jobs, Go source/seed/split parameters, GitHub workflow triggers, FORGE controller, runner and scheduled workflows remain unchanged.

## Stop and acceptance
- Run first-attempt full original 8/8 Linux/Windows qualification on this candidate, with one additional G162 focused Linux diagnostic. Capture exact per-test timings, source SHA/tree, parser receipt and evidence link.
- If the DEV diagnostic fails, report FAIL with exact classification rather than rerunning for favorable results.
- **Do not merge** this temporary profiling-only PR. Keep it draft, close after evidence is captured, and use findings to design the smallest substantive performance experiment. No science promotion, owner activation, deployment, or schedule.
