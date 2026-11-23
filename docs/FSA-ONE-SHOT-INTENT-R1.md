# FORGE FSA-05 — one-shot primary intent and restart classifier R1

**Source-only research safety milestone. NOT live autonomous science.**

`fsaintent` is a FORGE-only, deterministic one-shot primary intent state machine. It supplies immutable logical experiment identity (lane, candidate, generation, frozen source/prereg/cohort/fingerprint, bounded budget, unique correlation run ID) and a globally ordered append-only intent history that can be externally anchored by a future FORGE-private monotonic authority.

## Crash-safe protocol requirement

1. Independently qualify/admit the complete frozen experiment against a separately authenticated all-lane ledger and source provenance. The intent library does NOT implement authorization or qualify source.
2. Under a trusted FORGE-only writer, durably register `INTENT_PREPARED_NOT_DISPATCHED`. Assign its single stable run ID before sending any launch request.
3. **Before sending a possible worker launch**, persist `DISPATCH_MAY_HAVE_OCCURRED` atomically and verify its independently authenticated monotonic checkpoint. If persistence, checkpoint, readback, network, or worker acknowledgement is uncertain, **do not send or resend** the launch request.
4. After an independently verified immutable STARTED receipt, record `PRIMARY_START_WITNESSED`. After a separately verified original terminal receipt, record `PRIMARY_TERMINAL_WITNESSED`. Do not claim that a raw SHA-256 is a cryptographic signature or a receipt.
5. A crash after a dispatch-risk mark but before the original STARTED receipt must classify as `UNCERTAIN_START_RECONCILE_NO_REDISPATCH`. A trusted independent worker witness may reconcile the exact same intent/run ID, but a second primary launch is forbidden.
6. Any `START_INDETERMINATE` record also prevents redispatch; it can only advance on independently authenticated evidence for the already-allocated run, never on a timeout, automation wake, or replay.

Every stage is **non-authorizing**, including `PREPARED_NOT_AUTHORIZED_TO_DISPATCH`. Global immutable cohort and run ID conflicts are rejected across Wingless and Yggdrasil. No CKB-plane queue, KTRADE execution credentials, live broker, or scientific accepted-ref operation exists in this module.

## Verification and remaining deployment prerequisites

CI includes Linux race/vet/build and native Windows coverage. Deterministic tests exercise crashes at the prepared/dispatch-risk/indeterminate/start/terminal cuts; duplicate dispatch rejection; replay after restart; tampered journal records; valid-tail rollback against a distinct highwater; disjoint-lane operation; cross-lane cohort and run-ID collisions; and changed identities or budgets.

Tests use a **synthetic** `IndependentlyAuthenticated` flag and evidence digest; they do **not** supply a durable off-host CAS, a signer, an authentic START receipt, actual runner isolation, physical archive binding, independent original artifact custody or a live dispatcher. Until those external components are actually provisioned, qualified, and integrated, the library has no capability to start or accept science.

The full unattended Wingless+Yggdrasil lifecycle, retained negative outcomes, independent reviewer, bounded leases, failure-domain independence and concurrent noninterference with CKB/KTRADE remain mandatory FSA-04 acceptance gates tracked in issue #83.
