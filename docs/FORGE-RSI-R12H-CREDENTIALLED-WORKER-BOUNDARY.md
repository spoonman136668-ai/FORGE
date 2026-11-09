# F139 RSI R12-H — version-distinct credentialed authorization fence

Baseline protected main `58aae648045cb7ffb9dce428c45be8898f0bf02d`.
Original Windows release remains `42c70d74dd93ef90d0f4618fefefe2206b81eafe`.
Policy issue #807 currently authorizes only Wingless and Yggdrasil.

## Actual gate

The existing `forge-f139-development-worker.yml` endpoint gets a
strict `f139-rsi-` route, isolated from legacy execute, native V1/V2/V3
and concurrent Hybrid owner admission. The credentialed GitHub job
authenticates the R12-G pre-dispatch HMAC, exact R12-A binding,
candidate source bytes, GitHub dispatch run identity and SHA/tree, and
the independently fetched original owner issue #807. Its key is scoped
to that authorizer and NEVER passed to a candidate or credential-free
job.

**Fundamental limit:** HMAC verification is NOT cold original-owner
ledger custody. The GitHub authorizer has a copy of the HMAC secret;
therefore it cannot independently prove the original Windows owner
wrote its one-use R11/R12-G events. Supplied event sequences/digests
are NOT independently verified. The resulting receipt explicitly
reports `original_owner_sqlite_ledger_verified=false` and
`credential_free_worker_admitted=false`.

A distinct `rsi-execute` job is wired to the existing endpoint but
requires `needs.rsi-authorize.outputs.original_ledger_verified == 'true'`.
The authorize job only emits `false`: hence no source execution is
reachable now. The job contains an additional fail-closed invariant
check for the missing original ledger claim, never runs R12-F candidate
code or writes original owner state. Subsequent R12-I must deliver
an **independent original-owned single-use post-dispatch attestation**
before this can be made executable. It must be cryptographically
separate from the shared GitHub HMAC key or independently read the
real original owner ledger with authenticated original custody.

## Preservation

The current legacy owner dispatch still uses the original lanes and
identity schema. The established native V1/V2/V3 dispatch paths,
Wingless, Yggdrasil, and Hybrid are untouched. No new controller,
scheduler, queue, workflow, scheduled tasks, original owner release,
policy update, operator secret provisioning, paid API, scientific
first-use, source promotion or live FORGE-self attempt.

The strict packet is based on the existing `native_bundle` workflow
input, not a new API surface. A fail-closed current issue #807 is
expected. This engineering gate is **source-only** until independent
original release qualification and owner-signed runtime acceptance.
