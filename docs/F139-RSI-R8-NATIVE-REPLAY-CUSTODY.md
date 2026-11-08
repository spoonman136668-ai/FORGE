# F139 RSI R8 — native append-only repair observation custody (disabled DEV)

**Prerequisite:** R7 source discovery merged in protected FORGE \`main\`
\`1363cadc0f20155798ef52d72f85ac6df8a81ed6\`.
**Scope:** existing F139 \`Database\`, \`SingleOwner\`, original SQLite event
hash-chain, original \`GitHub.get\` and R6 original run+job+source verifier.
No new controller, scheduler, queue, workflow, installed owner or model call.

## Actual new custody

On a **new, disabled, empty development** F139 SQLite file only, the genuine
\`SingleOwner\` kernel mutex is required. A fixed run, original failed job,
GitHub run SHA and path are independently reread through R6 with no raw logs
published. The R8 method atomically appends one
\`RSI_FAILURE_OBSERVED\` record to the existing event chain, binding original
source, original Git blob, repair candidate SHA, failure log SHA, exact run,
attempt=1, job, mechanism, scoped evidence digest and prior chain head.

Every \`Database.verify()\` and cold \`Database.open_readonly()\` now audits the
R8 observation grammar and rejects duplicate \`task_scope_sha256\` or duplicate
run/job pairs even if they carry a different candidate, missing/invalid fields,
changing source epoch, fabricated authority, positive worker/first-use/merge
flags, over eight observations or invalid source ancestry. R7 can use the
persisted \`recorded_scopes\` as its consumed-set; a second authentic read of
the same failure fails. All negative tests exercise real \`SingleOwner\`
and file-backed WAL commits, rollback and cold reopen on both OSes. There
are no provider writes or execution privileges.

**Fail-closed actual original owner:** the only writer refuses ANY enabled,
legacy-suspended or nonempty owner ledger. The installed original task uses
source \`42c70d74dd93ef90d0f4618fefefe2206b81eafe\` and an enabled
immutable ledger, so R8 cannot be used to append there. The existing
controller \`run_once\` never imports this observation writer or calls R7.
The one-file owner verifier hook is source-only and not deployed.

## Nonclaims / future experiment

This qualification **does not** admit FORGE-self as a task lane, create a
worker ticket, send a job, change #807, install a source, perform scientific
first-use, resurrect consumed R13, claim original GitHub run provenance from
a forged fixture, prove genuine RSI, or turn unrelated CI failures into R6
SQLite repairs. Valid owner deployment would require an independently
authorized owner-source transition, typed policy for a distinct FORGE-self
development scope, a prospective authentic new failure and a real G0→G1→G2
matched frozen comparison per #1550.

**Engineering:** exact-head mandatory Linux+Windows full F139/GenEnv/native
regression and Go build/vet/test/race required.
**Science:** no heldout gain or learning/RSI acceptance.
**Deployment:** zero original owner changes; branch remains DEV.
