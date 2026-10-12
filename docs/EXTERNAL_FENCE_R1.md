# External fencing API boundary R1

`researchstate.CommitFenced` is an isolated source-only adapter that validates full journal state and requires an independently authenticated owner epoch, exact observed current head and atomic external compare-and-swap before returning a new proposed journal.

This package does **not** provide a deployed external authority, issue a fence, lease a worker, persist the proposed journal after CAS, witness a terminal original, launch science or transfer CKB ownership. A successful CAS is **not** authorization to dispatch. Unknown CAS outcomes quarantine the boundary without retry. A downstream worker must enforce the same authority epoch, and archive/journal durability plus witness must be qualified independently before use.

The historical CKB S14 first-use ledger is still authoritative; no re-run or inference of unconsumed status is allowed. All implementation remains on a non-production PR branch.
