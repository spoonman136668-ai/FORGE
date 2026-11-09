# F139 RSI R12-F — credential-free disposable source qualification

Original protected main `2350d967d0cbd7222f7e370e03a8a80a80a0650d`
(tree `da69c7d303afbabcc26dc1a07bbc93c2de7c2177`).

## What is actually implemented

The R6 known-repair proposal can now be staged using the R12-A/B bounded
source intent in a clean, exact-SHA/tree-pinned *local-only* FORGE Git
clone. The candidate must be ASCII Python inside the original allowlist,
pass real Python compilation, match the protected preimage/candidate SHA256,
change exactly one tracked file and leave the source checkout untouched.
The stage is committed only in disposable scratch; a content-bound
terminal receipt is durably written with all owner/worker/science authority
fields FALSE. It proves preparation and syntax, not successful regression,
source quality, original owner signing or RSI improvement.

Credential-bearing environment variables block even the disposable
rehearsal. No user-provided executable command, external network call,
new runner, new controller, new scheduler, automatic policy cutover,
original owner SQLite access, accepted source ref mutation, or paid API.
Existing R3 disposable Git staging and its fixed local command style are
reused; this R6-specific stage keeps its independent source allowlist and
preimage/candidate custody.

## Why NOT activated as the existing F139 workflow job

Open PR #1637 owns concurrent Hybrid changes to the same development
worker workflow. R12-F intentionally does NOT touch that workflow or
its original credentialed jobs. More importantly, an arbitrary
R12-E JSON witness cannot be upcast into original Windows owner authority:
the original one-use issuance lives in original SQLite, and the current
R12-E witness is nontransferable. A credential-free production job requires
a **distinct, authenticated original-owner-issued handoff** and an
unambiguous once-only terminal event, with separately qualified original
source transition and future issue #807 policy cutover. Merely adding a
FORGE-self choice and skipping secrets would create an unsigned bypass.

## Execution evidence and release bar

The exact candidate PR runs the mandatory existing Linux+Windows source
regression, F139 original controller qualification, and reusable
development rehearsal. Tests create real disposable Git repositories
and verify changed source, clean protected parent, failed tamper/replay
attempts and independent receipt. No historical failure replay, no
unobserved source promotion, no science first-use. A passing candidate
permits source-only merge, never live FORGE-self worker execution.
