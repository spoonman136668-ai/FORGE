# F139 V38 — exact original Windows owner one-shot read-only preflight

## Scope and source freeze

**Owner authorization:** In the 2026-11-14 FORGE integration chat the operator approved **one read-only original-owner preflight on the existing FORGE runner**, not source transition, Hybrid schema migration, policy change, task restart, new scheduler/controller, scientific first-use, or paid calls.

- Protected main parent: `c611c4362e3cc867984448a03ecdf3be923d2ef1`
- Protected parent tree: `f2f248c8d81654d88e943ed9b5ba9686225258c4`
- Existing original failed activation: run `43632986713`; **never retry**.
- Original committed source-only event: `#1830`, head `aaa60ef381c5a9f1e5296f56540ea9d73cef5a66f2562199d0cab81520abfadf`, source `c611c4362e3cc867984448a03ecdf3be923d2ef1`.
- Draft source-only repair: PR `#1759`, first-attempt CI PASS 12/12 at `e12c2e3fdd39c39994e5bc951bafa3eac4dd10d2`. Engineering CI is not original-host acceptance.
- Existing issue #807: only Wingless and Yggdrasil; no scientific first use.
- Frozen branch: `engineering/f139-v38-original-owner-readonly-once-20261114`.
- Allowed source paths: `.github/workflows/f139-v38-original-owner-readonly-once.yml`, `scripts/check_rar_g145_pr_scope.py`, `scripts/check_rar_g148_go_cache.py`, `scripts/check_rar_g156_dynamic_base_cache.py`, `f139/test_v38_owner_readonly_workflow_scope.py`, this document. G148/G156 only recognize this exact PR #1760 result; ordinary generic workflow/harness edits remain G145-denied. The new workflow blob is frozen as `087348d173fac524195cf72dc78df222c5851485`.

## Exactly one existing-owner read-only admission

Only the authenticated **original** GitHub issue #807 owner comment can trigger the added workflow on **protected main**:

```text
F139-HYBRID-V41-FORWARD-READINESS <exact-protected-main-merge-sha-of-PR1759> 6883036903
```

The accepted comment must be created after PR #1759 is merged with identical qualified tree and after first-attempt full Linux/Windows postmerge main CI. The runner must be `FORGE-CODEX-REMOTE` with `self-hosted, Windows, forge-codex-isolated` labels and the already existing original Windows owner profile. The unique job shares concurrency group with the existing V41 original-owner workflow and uses no schedules, automatic dispatch or extra consumers.

The workflow's only operation is `python -B -m f139.nci04_v41_hybrid_forward_readiness --target $GITHUB_SHA`. The CLI proves the disabled original task SID and source checkout, original owner mutex, exact source-only event #1830 and independent cold backup, historical 153 verified / 56 quarantined records, unchanged issue policy and zero database writes. An unavailable original machine, missing newer postmerge source, drift, stale comment, non-owner actor, API error or uncertain outcome is a hard HOLD, not permission to replay or synthesize evidence.

## Nonauthorization

A green workflow or CI does **not** approve a V38 source transition event, Hybrid DB schema migration, native activation, issue policy update, worker/experiment launch, enabled task, controller restart, or deployment. No source promotion or restart is attempted by this PR. Do not create new issue #807 owner comments while PR1759 remains draft and this workflow is unmerged; a comment then would be invalid and would not qualify.

## Qualification

G145 exact branch/base/tree, exact path inventory and exact read-only workflow blob remain a hard source gate. Full original Linux/Windows, native, dev qualification is required on the candidate SHA; then postmerge qualification is required for any later main source. Approval to run is distinct from creating a PR.
