# F139 RSI R12-H — credentialed pre-dispatch verification, source-only

Protected FORGE main: `58aae648045cb7ffb9dce428c45be8898f0bf02d`,
tree `f25d130089b3521b8ec8f66603268ee86dd272a9`.
Original Windows owner release still `42c70d74dd93ef90d0f4618fefefe2206b81eafe`;
operator issue #807 still authorizes only Wingless and Yggdrasil.

## Completed in this source-only gate

R12-H adds a deterministic credentialed-verification function and negative
tests for the R12-G pre-dispatch HMAC, exact R12-A candidate binding,
base64 candidate source hashes, GitHub actor/ref/run/attempt/source/tree
claims, original source-scoped operator policy, and a bounded canonical
input packet. It never executes the proposed source, modifies the
original SQLite owner, dispatches, or handles scientific first-use.

A valid HMAC alone **cannot independently prove** the one-use original
Windows owner ledger event. The same worker secret exists on GitHub's
credentialed authorizer. Untrusted original event seq/hash fields are
shape-checked but not verified against the original SQLite ledger.
The return explicitly declares original-owner ledger verification,
terminal receipt verification and credential-free worker admission FALSE.

## Mandatory protected workflow admission: G145

R12-H's initial candidate included a separate authorize/execute branch
in the original `forge-f139-development-worker.yml`. The mandatory
original Linux and Windows Go admission checks rejected this generic
workflow edit with `G145_GENERIC_PR_CHANGED_OR_UNRELATED_HARNESS`.
This is a **correct safety guard**, not evidence of a product Go failure.
The candidate was revised to restore the original workflow byte-for-byte,
rather than modifying G145, relabeling the PR, skipping the mandatory Go
checks or accepting failed qualification.

The currently merged F139 worker and native V1/V2/V3/Hybrid paths are
unchanged and FORGE-self remains unadmitted. Workflow activation
requires a **separately authorized** workflow provenance path that
respects G145; plus independent original-only one-use post-dispatch
receipt, installed Windows original source transition, source-pinned
owner policy and real fresh eligible failure.

No workflow dispatch, new controller/queue/scheduler, scheduled task,
paid model API, source promotion, secrets, first-use, or accepted
scientific result is introduced. Source-only PASS is not runtime PASS.
