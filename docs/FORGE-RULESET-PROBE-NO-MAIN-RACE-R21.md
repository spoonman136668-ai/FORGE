# FORGE R21 — remove same-commit status-check race

## Observed failure

After FORGE R20 merged at `6f2e3fd9376fdcd69aaaa3740ab3551ac09e8af5`, the new read-only proposal qualification workflow launched on the **same `main` push** as independent `linux`/`windows` qualification. It queried GitHub Check Runs **before** those required jobs reached terminal success and correctly returned `FORGE_MAIN_REQUIRED_CHECK_SOURCE_UNVERIFIED`. This is an ordering race, not evidence of a forged check or a reason to accept unfinished jobs.

Exact failing diagnostic: GitHub Actions `38465231484`. Successful prior exact-PR-head proposal diagnostic: `38464806524`. Full source qualification remains a separately enforced logical requirement, not replaced by this advisory workflow.

## Minimal repair

- Remove only `push: main` from `.github/workflows/forge-ruleset-readiness.yml`; keep PR and manual triggers.
- The PR diagnostic attests to the exact **already completed, independently pinned base/main SHA** with the same fail-closed check-run integrity rules.
- The universal `.github/workflows/qualify.yml` continues to qualify **every push to main** on Linux and Windows and every PR. R19's separate main-protection readback continues on relevant changed files.
- Add a regression test so a future code change cannot quietly reintroduce `main` push-trigger races or remove the main full-suite source qualification.

This does **not** make `main` protected or qualify the administrator ruleset (#175). No weakened signature/check-status validation, no original science, no paid API, no CKB/KTRADE mutations and no research-authority transfer. Acceptance requires this PR's full Linux/Windows regression + the exact PR-base read-only GitHub check-runs audit, and final merged-main full regression.
