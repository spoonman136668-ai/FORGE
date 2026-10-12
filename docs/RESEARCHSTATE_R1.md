# FORGE durable scientific lifecycle core — R1

Implemented `researchstate`: deterministic append-only, hash-chained lifecycle transition validation with optimistic expected-head compare-and-swap semantics; exactly two pre-existing lane identities (Wingless, Yggdrasil), immutable frozen identity, explicit irreversible dispatch-risk, quarantine, sealed evidence and negative/replay tests.

**Important boundary:** this is a pure offline journal and transition engine. It is NOT a durable transactional filesystem/database implementation, single-writer fencing, external witness, queue, worker, authoritative first-use ledger, automatic repair, or scientific activation. The caller MUST persist and independently witness the new journal head with true atomic conditional update before acting. A stale/ambiguous persistence result never authorizes dispatch. `Executing` records are hazard declarations only: no executable worker exists in this package.

Next qualified boundaries: persistent transactional store with crash fault injection and monotonic independent owner lease; actual existing-lane custody inventory and S14 ledger reconciliation; independently sourced authority; bounded execution workers and original-attempt receipts; evidence storage and automatic recovery/selection. Reuse existing CKB research lanes, never create replacement lanes. No CKB controller or KTRADE mutation in this increment.

S14 run 38281455598 failed in S74 before verified dispatch: `S69_FROZEN_PREREG_GIT_BLOB_CHANGED`. The workflow reports an indeterminate no-retry boundary. This is NOT evidence of unused first-use: operator-authoritative CKB durable ledgers and original receipts must be checked before any later original experiment action.
