# F139 V41 #1715 adjacent escrow custody (development only)

The original V40 Windows owner has an unadmitted Yggdrasil issue #1715.
This change makes the inactive V41/v36 source-transition verifier require
exactly one **immediately preceding** SHA-chained `NATIVE_PENDING_ESCROWED` event.
The event carries the frozen original ledger prefix, source-bound original issue
number/ID/ticket/intent, candidate target commit/tree, issue and comment digests,
and explicit `EXPLICIT_ESCROW_ONCE` disposition. It denies new dispatch,
unapproved reissue, scientific first-use and Hybrid admission.

The event **is not created** by this code. It cannot fake a VERIFIED or
QUARANTINED native task and cannot permit a silent source switch that leaves
#1715 unaccounted for. Existing original history remains untouched.

`Database.verify()` applies the escrow field grammar, and V41 source-transition
cold replay checks absence, uniqueness, event adjacency, original observed
event-1826 prefix, exact missing task and lack of prior native admission.

**Not implemented or authorized:** escrow event writer, issue reissue, signed
owner approval, release build/ref, existing Windows task stop/restart, source
switch, API POST, scientific experiment, or live first-use.

The later original-owner transition must atomically append the approved escrow
event and its V41 source transition under the same existing owner mutex and
SQLite transaction, with independent Windows backup/SID/task/binary/approval
verification, crash-recovery proof, complete negative tests and Linux/Windows
regression. A DEV-only escrow receipt is not release authority.

Current immutable V40 source: `2c7caad5a4502d4b874a11d57207a35cf033eb08`.
Development base: `446fc7ba2cc1a1f874839067a30611f14b151223`.
