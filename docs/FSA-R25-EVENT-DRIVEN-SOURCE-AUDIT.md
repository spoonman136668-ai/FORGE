# FORGE R25 — Existing auditor event-driven qualification fallback

The installed R21 source auditor already runs from `.github/workflows/forge-automerge.yml` with a read-only GitHub token, on the trusted default-branch SHA, and with its existing ten-minute GitHub `schedule` definition. GitHub has not yet emitted a new observed `schedule` event since R21 promotion on October 15, 2026. The prior scheduled run belongs to an older SHA.

R25 **does not add a controller, scheduler, workflow, token, permission, external app or paid model**. Instead, it adds a GitHub-native `workflow_run: completed` event **to that existing audit workflow**, bound to the existing `FORGE FSA-source qualification` job. After the independent FSA-source Go acceptance succeeds, GitHub can now immediately run the same read-only auditor against authentic current PRs. The job still verifies it is executing from `refs/heads/main` at `github.sha`, only reads fresh GitHub REST data, and re-validates source SHA/branch/base plus both successful workflow job sets. It does not trust any workflow-run artifact, output or PR comment as authorization.

For `workflow_run`, a non-successful upstream run is skipped; `schedule` and `workflow_dispatch` are unchanged. The workflow has `contents:read`, `pull-requests:read`, `actions:read`, unchanged concurrency, and no GitHub mutation calls. `MergeAuthorized=false` and `ScientificAuthority=false` remain unconditional. Incomplete bypass-actor visibility still denies merge permission.

## Genuine acceptance

After R25 is merged with the exact-head Linux/Windows and R21 source auditor regression PASS, create a **new benign source-only eligible PR** to automatically generate a successful FSA-source `pull_request` workflow run. Then observe the **actual** `workflow_run` trigger of the installed main-branch auditor and verify its logs contain the exact new candidate SHA, `SourceTestsQualified=true`, a real policy readback or explicit `RULESET_BYPASS_VISIBILITY_MISSING`, and no mutation. Do not call an R25 PR-triggered test an authentic controller event.

The separate schedule acceptance stays open until a real `schedule` run on the installed SHA is observed. Event-driven production operation does not require inventing schedule evidence.

This does not dispatch Wingless or Yggdrasil science, authorize new experiments, modify Cloudflare, KTRADE, CKB-plane, or call Codex.
