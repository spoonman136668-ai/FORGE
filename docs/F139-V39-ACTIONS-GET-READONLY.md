# F139 V39 — one-shot original Windows GitHub ACTION_RUNS read-only diagnosis

## Observed original-owner failure

The fresh V4 original-owner comment `6892377331` produced first-attempt
[run 43699712064](https://github.com/spoonman136668-ai/FORGE/actions/runs/43699712064),
which stopped with `F139_V38_TASK_SNAPSHOT=AUTH_PROVIDER`.
Its sanitized native CLI terminal record was:
`ACTION_RUNS / GITHUB_API_FAILED / exit 1 / HTTP status unclassified / attempts 1`.
The original task and SQLite were not inspected. This is not a controller or
Hybrid scientific outcome. The V4 event is consumed and must not be replayed.

## V39 exact purpose and bounds

One new `issue_comment: created` workflow (no schedule, dispatch, controller,
queue or consumer), using the **existing** original Windows
`FORGE-CODEX-REMOTE` runner, uniquely isolated concurrency and a fresh
`OWNER`-authenticated issue #807 comment.

After verifying the GitHub signed event, exact clean protected-main checkout,
unchanged original owner-profile blob
`9bda78341bc3651e8b7b0a24ea6c7858dbff05c6`, unchanged prior V38 workflow
blob `6857bf5c81d9662f7cf26f4a07eb59e463ac8253` and the unchanged
Wingless/Yggdrasil two-lane issue policy, one single subprocess invocation
per route performs exactly three GitHub CLI **GET** reads:

* Current fresh issue #807 owner comment metadata
* V4 read-only workflow run `43699712064` (expected failed)
* V3 read-only workflow run `43696957491` (expected successful)

Each CLI process uses the same `gh api repos/.../actions/runs/<ID>` shape
as the failing original provider. No retries, writes or provider changes.
Only static labels can leave: OK, HTTP_AUTH, HTTP_NOT_FOUND, HTTP_LIMIT,
HTTP_SERVER, HTTP_OTHER, RATE_LIMIT, TRANSPORT, CLI_AUTH, CLI_ARGUMENT,
CLI_OTHER, CLI_MISSING, SPAWN_FAILED, TIMEOUT, INVALID_JSON,
INVALID_RESPONSE, OVERSIZE or INTERNAL. No URLs, responses, tokens, raw
stderr/stdout, paths, task records, SQLite data or process identities are
logged. A successful Actions job is **only diagnostic execution**, never
original task acceptance or permission to activate Hybrid.

## Release conditions

Source-only PR #1768 on protected-main baseline
`7b2b6bbd707ba80613b6f305615e9e8167b7ffaa`
(tree `fccf8c779110ceaa34dd13680d841b9c1cc40ea3`)
changes exactly seven paths with G145/G148/G156 source admission,
owner blob pinning and negative controls. It requires first-attempt full
Linux/Windows native regression on exact candidate, matching-tree source merge
and first-attempt 8/8 postmerge regression before any owner-host GET.

Only then may the authorized fresh owner intent be:

```text
F139-V39-ACTIONS-GET-DIAG <qualified-merged-main-sha> 6892377331
```

Keep the original controller held and issue #807 two-lane/first-use=false
regardless of result. Separate scientific, runtime and deployment gates still
require independent provenance; do not treat GitHub CLI health as admission.
