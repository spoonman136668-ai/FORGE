# RAR G176 — F34 exact-source F10 canonical-validation and full Go regression (DEV only)
Date: 2026-11-09. This protocol is frozen before the first G176 measurement. It does **not** precede the already-existing F10 implementation; it reuses the prospective G174 ≥1.50× performance criterion unchanged on new source.

## Provenance and hypothesis

- Protected FORGE main: `4adc6d8b7397e555deee46440bbce40ff2265f39`, tree `5f081e222f8b55cb3af67c02643c0149cfa5b192`; original CI G145/G141/G144 guards remain authoritative.
- Unmodified independent Eureka F34 baseline: `9f04db87a01701b458bd4aa6b1c4428b06a3c17e`, tree `f690239ebf9121c653e2305f1527cb6112cb9fb9`. F33 scientific DEV_NO_GO, F34 custody forensic result preserved.
- Candidate F34 plus exact already-qualified F10/F11/F12 read-only canonical-validation optimizations: `9913e6c0c645beff2d423de5d07d3ddc580cb905`, tree `2ef06c0910e4cc6cf6ef1cbec60b3592249a00d9`. Exactly seven changed paths relative to F34: three production Go, three additive cold/forged/concurrency tests, frozen G174 preregistration document. F33/F34 science files/tests/docs unmodified.

## Frozen tests / threshold

1. Exact-SHA/tree clean detached worktrees for original and optimized source, Go 1.23.12 on each of Linux and Windows. Same OS/toolchain/GOFLAGS=-p=4/GOMAXPROCS=2/GOMEMLIMIT=1536MiB, original first then candidate.
2. The existing original `go test -race -count=1 -json -run '^TestF10NoOwnerAdmissionByTamperedOrRehashedDevelopmentEvidence$' ./nativediscovery` on both sources. Require ≥1.50× original/candidate elapsed on EACH OS, exactly 24 original pass/fail/skip test events (parent + 23 rehashed source/science/owner/seed/score/negative subtests) preserved with identical names/outcomes. No post-result retune/retry.
3. Source diff exactly seven frozen paths; original F10 benefit test blob unchanged, original F33/F34 Go and preregistration blobs unchanged; cold independent development, forgery recovery, 8 concurrent validations under race PASS. No changed first-use or scientific decision.
4. Candidate detached worktree on BOTH OS: unfiltered original `go test -count=1 ./...`, `go test -race -count=1 ./...`, `go vet ./...`, `go build ./...`. Same source tree must be reverified clean afterward. Preserve full output and failure. No predictive test selection.
5. CI-only original qualified main-target PR runs all original 8 Linux/Windows native, F139, GenEnv and aggregate jobs. Existing Linux G141 180s/4GiB and Windows G144 run unchanged **on the CI-only harness source**, not on detached F34 research source. Distinguish those sources; do NOT claim F34 exact-tree native G141 qualification from the detached tests. 
6. A CI-only branch may change exactly six isolated engineering files: `.github/workflows/qualify.yml`, `scripts/check_rar_g145_pr_scope.py`, `scripts/check_rar_g148_go_cache.py`, `scripts/check_rar_g156_dynamic_base_cache.py`, this G176 document, and the pre-existing G174 development document. Keep original security and negative controls and require exact protected-main base ref. No changes to production FORGE Go, active research, owner, FSA, runner, scheduler, science first-use or deployment.
7. Record first-attempt execution time, event parity, Go full source status and artifacts. Original F34 unoptimized Linux G141 timeout remains genuine FAIL. No claim of 2× whole-process improvement absent a matched full-pipeline A/B; no merge or promotion without independently scoped research-owner and exact-tree approval.

**Decision:** ≥1.50× both OS + full candidate Go suites and original eight-job CI PASS -> F34 source-bound engineering DEV PASS only. Otherwise NO_GO, preserve first failure.