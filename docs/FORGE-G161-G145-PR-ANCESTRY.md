# G161 — bounded PR Git ancestry retrieval without loosening original qualification

## Source freeze and policy
- Exact original `main` source `ad9026d2e551b054fc944d536ded37fe20a1aaa4`; Git tree `9f7ac8adb3a2665cf86c92c47fef482f6097feb5`.
- Five files only: `docs/FORGE-G161-G145-PR-ANCESTRY.md`, `.github/workflows/qualify.yml`, `scripts/check_rar_g145_pr_scope.py`, `scripts/check_rar_g148_go_cache.py`, `scripts/check_rar_g156_dynamic_base_cache.py`.
- Branch: `engineering/rar-g161-verified-pr-ancestry-20261109`. Same-repo read-only qualifying source; no new scheduler, runner, test engine, Go source or execution authority.

## Authentic failure and two distinct classes
- In original 42584602226 source `15de26d02d1811a8c5ce3c189adf7cd111e9f8ff`, the G145 PR event base `aa624323b00d43e43499af842bf9af6974ec6913` is a **real ancestor**, confirmed by GitHub compare: 84 commits ahead, zero behind. But original Linux Go qualifier checked out only eight commits, and its local `git merge-base` failed `fatal: Not a valid commit name`; this is a false negative caused by source-history absence and NOT a failing Go package or timeout.
- In original 42585161170 source `b7fa2afd29a3236c6744b4b189061b0363e4df89`, the event base `ee1ede1af2a552a37cb4f1c27d9e02e8b5d3ebb4` is **not an ancestor**: GitHub compare shows diverged, one ahead / four behind. G145 must continue to reject such source even if its history is locally available.

## Change and frozen invariants
- Only `linux_native` and `windows_native` checkout steps fetch up to **128 commits for PR qualification**, preserving original eight-commit depth for protected-main pushes and four F139/GenEnv jobs.
- 128 covers the observed authenticated 84-commit ancestor span with bounded overhead. It is not a guarantee for unbounded histories: older, non-ancestral, or missing sources continue to fail closed and may require authorized source synchronization.
- No change to `admit_original_pr`, `github_event_base`, source SHA/tree proof, G145 negative controls, exact diff, Go test/vet/build and full-package parity, G141 180s runtime limit, 4 GiB cgroup cap, Windows G144, job timeouts, workflow trigger, cache keys, isolation or scientific authority.
- G145/G148/G156 changes are exact-name five-file frozen engineering-admission exceptions only, preserving generic-PR denial of any harness/workflow rewrite.

## Acceptance
1. Inspect exact diff: exactly two `fetch-depth` lines in six-job workflow, both conditional; all original test and workflow instructions unchanged. All other changes are immutable admission metadata and this protocol.
2. Current exact candidate first-attempt original eight-job Linux/Windows regression PASS; check original source/negative controls.
3. Merge only with verified same parent/head/tree and supported FORGE engineering authority. Original protected-main first-attempt eight-job qualification PASS and independent F73 cryptographic origin PASS.
4. Metric: record candidate and postmerge full end-to-end CI wall-clock time and compare to historical 264-second baseline. Preserve 2x objective where feasible; do not attribute all time gain to ancestry depth.
5. Direct frozen failure-path acceptance must remain **UNVERIFIED** until naturally exercised on a valid PR with more than eight ancestors. Do not rerun, edit, rebase or merge Eureka science just for this check. Stop on actual source or CI failures.

No scientific experiment, model training, original scientific first-use, deployment, workflow schedule, owner, or research loop change is authorized by this PR.
