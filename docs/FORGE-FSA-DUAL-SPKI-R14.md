# FORGE R14 — reject shared TLS server identity across FSA peers

R14 hardens the previously source-qualified independent dual-mTLS observer without changing its negative-only authority posture.

## Defect
`fsaremote.NewClient` checked that authority and witness had distinct HTTPS endpoint URLs but could accept **the same pinned server SPKI** on two hostnames. Two endpoints controlled by one TLS private key must not satisfy even the structural dual-peer trust contract.

## Bounded repair
- Reject equal authority/witness `ServerSPKISHA256` identities even when endpoints differ.
- Preserve rejection for same URL, missing roots, untrusted TLS and same Ed25519 witness/authority signing key.
- Make an unprovisioned nil remote observer fail closed with an explicit error rather than panicking; add a regression test.
- Extend the existing remote-client construction test to prove that two URLs with one TLS key fail, and the distinct-key synthetic transport continues to construct.
- No new network requests, credentials, original execution, queue, accepted reference, FSA deployment or old-owner revocation.

Exact-head Linux tests/race/vet/build and native Windows tests/vet/build plus full public isolation are mandatory. A green result qualifies **only** this source-level trust-separation repair; physical host/storage, independently controlled keys, monotonic CAS, consumed-source birth, true side-effect fencing and 24-hour research soak remain unproven.
