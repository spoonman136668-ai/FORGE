# FORGE durable original-first-use custody — R1

This is the **storage mechanism**, not a replacement research authority. It handles only the existing Wingless and Yggdrasil lane identities; no new lanes, experiment starts, queue consumers or worker launchers are created.

## Implemented

- Externally signed reservation grants bind exact original experiment ID, immutable frozen scientific identity, original intent digest, owner/epoch, and expected immutable journal head.
- The store checks a separately provisioned Ed25519 public key. No production private key, signer, deployed authority server or self-authorization exists in this implementation.
- Create-only, file-synced, sequential hash-chained custody records preserve the **original grant signature** for restart-time reauthentication; hashes alone are not accepted as provenance.
- `ORIGINAL_RESERVED_NO_REPLAY` is irreversible: the same original within its existing lane cannot be reserved again, even after worker silence, crash, restart, ownership epoch changes, or repository commits.
- Read-only recovery verifies every journal record, sequence, previous head, signed grant, canonical encoding, owner-epoch monotonicity and unique original IDs. Torn, missing, extra, symlinked and corrupted journal entries fail closed.
- One process-local exclusive writer. A crash leaves a lock; it is never reclaimed by timeout without independently witnessed fencing. Unknown write outcomes poison the writer and bar clean shutdown.

## Before any activation

**Inactive source-only prototype.** The local file lock is not distributed ownership fencing, and a successful file sync does not establish all-filesystem power-loss transaction durability. The independent durable authority, external high-water witness, atomic owner transfer, worker-side epoch enforcement, first-use ledger import and qualified crashed-owner recovery remain missing.

Reconcile the real historical CKB first-use and consumed ledgers first (including ambiguous S14). Preserve prior results, negatives, existing lanes and scientific scope. Run native Windows filesystem fault injection and a final integrated regression. Obtain explicit qualified cutover approval before any FORGE science execution. GitHub Actions success is not proof of autonomous scientific progression.

The test signing key is synthetic and cannot authorize research. No production authority, broker access or KTRADE logic is changed.
