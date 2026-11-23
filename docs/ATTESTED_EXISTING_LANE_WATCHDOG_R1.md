# Signed existing-lane watchdog observations R1

The observed CKB execution ownership and the two original Wingless/Yggdrasil lane identities are pinned. This integration requires separate independently provisioned Ed25519 observation-signing keys and exact immutable source commits, original queue IDs, owner IDs, owner epoch, journal heads, monotonic sequence floors and fresh timestamps. The strict verifier runs the existing watchdog only after verifying BOTH signed lane attestations. Output remains shadow-only.

The collector cannot assert a trustworthy worker heartbeat. That signal is rejected until worker-origin signed receipts are joined independently. A missing heartbeat can trigger reconciliation, never retry. Tests cover signature tampering, swapped signing keys, replayed/stale observations, queue substitution, owner drift, cross-lane duplicates and first-use-safe diagnostics.

**Not active:** This is a verified read-only diagnostic seam, not an independent witness deployment, signing key provisioner, durable epoch service, evidence authentication authority, worker executor, or scientific cutover. Original S14 custody and previously consumed cohorts remain under CKB-plane. No new scientific lanes, accepted ref mutation, CI-triggered scientific work, or live KTRADE change.
