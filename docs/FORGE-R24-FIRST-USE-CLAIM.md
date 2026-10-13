# FORGE R24 — durable local original first-use claim (not science launch)

This source gate introduces a **persistent local first-use claim** with exclusive creation, file sync, directory sync, exact canonical identity and tamper rejection, and checks signed independent STARTED/TERMINAL worker receipts via the existing `workerreconcile` verifier.

Acceptance tests exercise 64 concurrent duplicate claims (exactly one can commit), restart duplicate rejection, changed identity and corrupted claim rejection, untrusted directories, no-receipt ambiguity, valid STARTED/TERMINAL classification and forged terminal signatures. A TERMINAL receipt is **not** independent scientific acceptance; it requires later evidence and preregistration verification.

**Critical limitation:** Filesystem exclusivity does not implement cross-host linearizable CAS, and this package deliberately launches no experiment. It proves a bounded building block, not genuine scientific original execution, scientific acceptance, unattended 24h continuity, or controller cutover. An actual experiment must not start until a separately qualified shared owner/first-use boundary and independent scientific validator are integrated and tested against real workers.

External FSA/Cloudflare remains deferred by user request. This implementation neither reactivates it nor touches CKB-plane, KTRADE, Wingless, or Yggdrasil.
