# FORGE independent mTLS FSA read-only service handlers R1

Implements the missing server-side HTTP interfaces for the existing `fsaremote.Client`, without weakening first-use or scientific acceptance controls.

- `fsaservice.AuthorityHandler(pin, clientSPKI, store)` serves strictly authenticated GET `/v1/fsa/anchor` and GET `/v1/fsa/binding?archive_id=<pinned>` from a separately provisioned authority backend.
- `fsaservice.WitnessHandler(pin, clientSPKI, store)` serves strictly authenticated GET `/v1/fsa/highwater?archive_id=<pinned>` from an INDEPENDENT witness backend containing an ALREADY SIGNED, monotonically retained high-water checkpoint.
- Requests are rejected unless the TLS stack reports a verified client certificate chain and the client SPKI SHA256 equals a separately configured pin; strict archive ID, signing key, binding, authority epoch, revision floor, Ed25519 witness signature and returned anchor bounds are checked. No opaque original-science evidence is sent in the HTTP replies.
- The existing client independently verifies both peers' TLS roots and distinct SPKI pins, and cross-checks the witness against the authority anchor.
- HTTP POST `/v1/fsa/cas`, key issuance, worker starts, science activation, original-first-use replay, and all other mutating operations are **not** exposed. A successful read-only service cannot advance a scientific journal.

An integration test starts **two different TLS servers** with separate certificate private keys, enforces real mutual TLS client-certificate checks and transport SPKI pinning, uses the actual `fsaremote.NewClient` against both HTTP services, confirms an authenticated anchor/binding, rejects a forged witnessed checkpoint and wrong server pin, rejects a caller without a client certificate, and confirms that attempting CAS does not mutate the authority.

## Deployment and authority boundary

These are library-level handlers, not running services. They **require** operator-provisioned TLS server/client certificates, separately protected signing identities, and independently deployed, authenticated, durable authority and witness storage. Test in-memory stores/keys are fixtures and must NEVER be selected for production. This commit cannot verify physical failure-domain separation or restart-safe monotonic persistence merely by using two network origins. The existing FSA source-verified signed scientific checkpoint protocol and external atomic CAS still require separate qualified backing before write capability is admitted.

Neither CKB nor the old Wingless/Yggdrasil research lanes are touched. No new authority or scientific worker is activated, and KTRADE remains paper-only.
