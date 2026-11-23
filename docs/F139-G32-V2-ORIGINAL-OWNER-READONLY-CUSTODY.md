# F139 G32 — read-only original owner + V2 provider custody review

Source-only, nondeploying qualification stacked on G30 and G31 draft
branches. No release, controller/task/ledger write, queue, scheduler,
worker dispatch, signed permit issuance in production or scientific first-use.

Reads the genuine original Database SHA-chain and exact native admission
event (after production head 220), freezes the original issue and candidate,
requires the real WAIT_PROVIDER transition sequence and reconstructs the
preexisting owner V1 native HMAC from the original owner credentials and
event history. This is not authorization for V2 execution by the V1 signer:
G31 independently verifies the extra domain-separated V2 HMAC and binds
the owner event sequence/hash, epoch and run. G32 then checks independently
supplied provider ZIPs under the already existing G14 strict V2 reader for
Linux and Windows, reporting successes and negatives without promotion.

Hard limits and remaining gaps:
- Caller MUST actually hold original SingleOwner mutex and authenticate
  the installed source and GitHub workflow/run/job/artifact identity itself.
  This module cannot independently prove that a provided ZIP came from
  GitHub or that an event hash was not extracted from another context.
- No V2 signed owner dispatch has occurred and original issue #907 stays
  quarantined. The original ledger is still protected on main at b2079282.
- G30's development-only output filenames and G14's expected canonical
  V2 provider ZIP filenames are not yet connected by a production worker.
  These synthetic tests use genuine archive verification on constructed
  fixture ZIP bytes, NOT an authentic provider execution.
- This code does not write the owner ledger or admit a V2 terminal.
  In particular a V1 VERIFIED terminal is rejected as V2 proof.
- Tests use a fresh disposable SQLite database, a synthetic historical
  prefix extended to simulate post-220 events, and synthetic signed
  provider fixtures. No historical event is replayed in the real ledger.
- Strict independent FSA first-use remains separately DENIED.

For actual unattended development, the remaining gate is a separately
qualified V2 Actions workflow + exact ZIP packaging, independently
authenticated provider metadata and original-owner V2 terminal writer,
followed by a guarded source migration and two genuinely fresh natural
candidate admissions. Maintain 2 starts per 10 minutes and no paid API.
