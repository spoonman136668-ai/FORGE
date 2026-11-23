# FORGE R25 — real process interruption and independently recomputed bounded evidence

A real Go test subprocess consumes the R24 durable local first-use claim, signs its STARTED receipt, and signals after the durable record. The parent deliberately kills that OS process. A **new process** independently verifies the signed STARTED receipt and quarantined disposition, and a second new process tries and fails to claim the same original. No terminal result is invented after the crash.

A separate original executes a bounded deterministic 1..1000 sum-of-squares computation. Another independent OS process recomputes the result, verifies its exact file bytes against a signed TERMINAL receipt and verifies claim identity. The scientific acceptance flag remains false, and all computations are explicitly **NONSCIENTIFIC TEST FIXTURES**. A duplicate completed original is rejected.

This closes only process-level recovery and bounded-evidence integration. It does NOT execute a real Wingless or Yggdrasil original, prove shared durable original first-use across machines, establish independent sealed scientific acceptance, grant authority or activate external FSA. CKB-plane remains owner. CI must pass on native Windows and Linux and after protected-main merge.
