# ISO-04 — Retire final runnable CKB S14 dual-source reconciliation entrypoint

**Standing boundary:** FORGE is independent of CKB-plane. Mind-Palace is its only permitted optional direct, read-only, commit-pinned *advisory* context bridge; neither external context nor this gate grants scientific first-use or acceptance.

## Source finding and remedy

After ISO-02 and ISO-03, `cmd/forge-ckb-s14-reconcile/main.go` still parsed absolute installed controller ledger paths and local hash pins, constructed a `ckbhistory.New(token)` GitHub client and called `ckbreconcile.ReconcileWake`. It could reach the private controller with a caller-provided token and local CKB state, violating the permanent architecture.

ISO-04 turns this **executable command** into an unconditional denial. All former arguments, local paths, output writers and tokens are ignored. It cannot read any local files, issue network calls, or emit provenance/first-use claims. Linux and Windows tests run adversarial legacy arguments and tokens, assert the precise blocked error and zero emitted output. The existing required `isolationguard/check.py` now rejects the removal of the retirement sentinel, reintroduction of original local/remote client APIs, or removal of the inert command.

The historical `ckbreconcile`, `ckbhistory` and `ckbcustody` **library source and historical Git commits** remain for archival reproducibility, not as a live FORGE science adapter. This gate changes no science result, evidence archive, Wingless/Yggdrasil program, Mind-Palace repository, Cloudflare service, optimizer, original-start permit or worker schedule.

## Acceptance and nonclaims

The source must pass the exact PR-head hosted adversarial isolation checks, Linux and Windows full Go test/vet/build suite, branch safety and protected-main qualifications. Historical-library retention and removal of an executable route **do not imply every possible implicit future dependency has been proven absent**; code review and permanent CI guards remain necessary. No cross-repository credentials, CKB repo access, live first-use, acceptance or optimizer promotion are needed or conferred.
