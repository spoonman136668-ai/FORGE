# F139 G31 — Separately signed V2 execution-intent permit (source only)

Base: completed G30 V2 development bridge PR #938 at
5d889547399cdb52c646d571ad978caa1714b6f1 (all six Linux/Windows
qualification checks PASS). This G31 change is chained after G30 to avoid
conflicting source modifications on protected main.

A V1 native signature and NativeAdmission alone cannot grant future V2
execution. G31 introduces a distinct, explicit owner-issued HMAC-SHA256
domain for V2 execution semantics. The V2 permit binds the originally
verified native admission, source and exact donor commit/tree, complete
native candidate identity, intended V2 receipt protocol, owner epoch,
independent original native-admission ledger event sequence/hash, and the
exact provider run ID and runner OS. No signing key is serialized.

Crucial replay guard: only original owner admission events STRICTLY GREATER
than the observed original F139 production activation head 220 are eligible.
This categorically excludes prior consumed G1/G3 issue #840 and #907 and
other historical negative original work. The original caller must verify
the ledger event kind, hash chain, original signed issue/source/intent and
exclusive native ticket under its existing single-owner lock. Supplying
an arbitrary sequence/hash string is NOT proof of any authentic custody.

The independent verifier checks canonical exact-key JSON, rejects duplicate
keys, enforces the expected immutable owner/source/event/run/candidate
binding, and compares the domain-separated HMAC in constant time.
Synthetic tests demonstrate that a genuine V1 native HMAC cannot validate
as the V2 permit; tampered source, ticket, issue, epoch, event hash, runner OS
and action information fail closed.

This module is NOT wired to the live original-owner controller, workflow,
GitHub Actions, worker V1/V2 CLI, V1/V2 receipt parser, accepted references
or scientific first-use. Running the verifier with an owner key must happen
only in the original authorized owner/authorization environment. The
credential-free V2 worker must NEVER see the HMAC key. The result alone is
not a provider terminal receipt or scientific authority.

Next gate: original owner/source-only end-to-end admission and versioned
provider custody qualification, with a truly independent signed original
owner event, no replay, no work from invalid/negative tickets, then one
full cross-platform final regression and separately authorized guarded
release. No new controller, scheduler, queue, paid API or experimental
scientific-first-use is authorized by G31.
