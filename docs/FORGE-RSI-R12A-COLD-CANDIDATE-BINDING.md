# RSI R12-A: original-ledger candidate binding (development, inactive)

Parent protected main: `53b7a0d340f541de85a40de9dcafdd1a97638e52`.
Scope: one additive read-only candidate-binding module and negative tests.

R11 authenticated original-owner reservation is now cryptographically
cross-bound to the same R6 provider readback candidate fields: original
failed main SHA, run/job/log, blob path/hash, unchanged source hash,
candidate source bytes/hash, task scope, mechanism, and owner ledger event
sequence/hash. An authentic R11 historical foundation and a cold Database
verification are prerequisites; fake disposable ledgers cannot authorize.

This is NOT a signature, HMAC, new worker ticket, queued job, a new owner
lane, a replay token, a worker execution path, CI qualification, source
promotion, native scientific first-use, or RSI proof. The emitted dict marks
all such capabilities false. R11 already keeps the original owner's
one-reservation lifetime cap; this read-only code neither consumes the
reservation nor provides replay protection for hypothetical worker jobs.

A future R12-B original-owner signer and credential-free worker admission
must separately bind a *single* original job/attempt to its sealed lifetime
reservation and terminal receipt. Until then, the F139 signer, owner schema,
and verify_ticket allowlists remain byte-identical and reject FORGE-self.
No live failure currently qualifies after the R10 cutoff. Do not forge one.

Qualification: focused unit tests, mandatory original complete Linux/Windows
regression and build on the exact candidate SHA. No change to source
promotion, owner tick, scheduler, research queues, Wingless or Yggdrasil.
