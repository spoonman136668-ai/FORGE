# FORGE witnessed read-only watchdog CLI

`go run ./cmd/forge-lane-watchdog --pinned /absolute/pins.json --claims /absolute/signed-claims.json`

The CLI requires two separate original-lane pinned identities with Ed25519 public witness keys and fresh independently signed observation files. Both original Wingless and Yggdrasil program identities, queues, source commits, CKB owner epoch, exact journal heads, and sequence floors must match. Output is an inactive diagnostic report only.

The CLI has no built-in private signing key, mock production signer, worker launcher, mutable authority API, broker connection or scientific dispatch functionality. Pin provisioning and independent live CKB observation signing are NOT deployed or qualified; the command does not collect actual evidence by itself. Passing a self-authored pin file is not proof of trusted external source provenance. A production operator must pin the keys and identifiers through an independent qualified provisioning channel. A separate durable high-water store must maintain the monotonic sequence floors. Two test fixtures demonstrate diagnosis and forgery rejection.

CKB-plane remains the sole scientific authority until a separately authorized and verified cutover. Historical first-use, including ambiguous S14, is not retried.
