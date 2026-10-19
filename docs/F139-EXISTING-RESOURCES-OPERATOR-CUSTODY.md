# F139 owner custody using infrastructure already established

This gate **does not require ChatGPT Work access, another Cloudflare account,
another controller, a paid API, a new VM or an additional GitHub runner**.

## Actual resources and independent roles

- **Existing always-on Windows workstation:** sole F139 scheduling owner. A
  native Windows CurrentUser-DPAPI-protected Ed25519 operator key is provisioned
  on that workstation, never in the public FORGE repo or GitHub Actions. It can
  attest operator *possession* and supply an independently pinned public key.
- **Existing Cloudflare Worker/D1:** retain all six archived scientific originals,
  seals and an independent FSA global first-use high-water and eventual distinct
  witness identity. It is **not** the controller.
- **Existing GitHub Actions:** run bounded, source-pinned qualifications and use
  the existing Cloudflare API credentials for provider operations only after
  separate authorization and explicit protections. CI identity/OIDC is **not**
  an independent scientist or cryptographic signer.
- **Existing private rbackup:** intended durable off-provider storage for
  encrypted D1 exports and verification manifests. GitHub privacy by itself
  is not encryption or isolated restore proof.

## Windows owner key ceremony (one-time, NOT YET EXECUTED)

Run in the operator's normal Windows account, from an exactly qualified FORGE
source checkout, using its existing Go installation:

```powershell
$ErrorActionPreference = 'Stop'
go run ./cmd/forge-fsa-owner-key init
go run ./cmd/forge-fsa-owner-key prove
```

The first invocation generates an Ed25519 owner identity with cryptographic
randomness, protects its 32-byte seed with **Windows CurrentUser DPAPI**, and
writes the encrypted blob under
`%LOCALAPPDATA%\FORGE-FSA\owner-ed25519.dpapi` using exclusive creation. It
**refuses to overwrite** a prior identity. The second prints only the public
Ed25519 key, its SHA-256 fingerprint and a domain-separated possession
signature. No private signing bytes are printed or sent to GitHub.
A native-Windows CI test independently checks DPAPI roundtrip, no-overwrite,
tamper rejection and Ed25519 signing and verification.

This local key is a **single operator root**, NOT the independently controlled
external FSA witness. It is bound to the Windows user/profile/machine and has
not been recovered across an OS/profile failure. The emitted receipt
deliberately states
`external_witness_verified=false`,
`independently_recoverable=false`, and
`scientific_start_authorized=false`. It is a bootstrap possession proof, not
a live original permit.

## Operations that use existing resources but remain separate

1. **Real recovery:** export the existing D1 through the existing Cloudflare API
   credentials using Cloudflare's documented D1 export polling protocol.
   This is a stateful provider operation and can pause D1 queries temporarily;
   it must be scheduled, securely encrypted *before* being written into
   `rbackup`, and independently restored and verified. D1 Time Travel
   availability alone is not the off-provider encrypted recovery proof. Never
   put plaintext D1 export or decryption/signing keys in GitHub logs, public CI,
   source files or temporary nonencrypted artifacts.
2. **Separate witness:** provision and authenticate a distinct
   Cloudflare-owned witnessing key/monotonic receipt and pin the independent
   Worker/D1 source identity. It must not merely trust the workstation's
   self-declared fingerprint or GitHub's CI OIDC subject. Key custody and the
   operator's public pin must be verified through different failure domains.
3. **Complete history:** reconcile every consumed, active and
   indeterminate Wingless/Yggdrasil original. A report about accessible
   GitHub runs is not a complete all-lane scientific ledger.
4. **Guarded additive migration:** after real backup/recovery and independent
   custody are verified, apply only the six already-qualified `fsad1` DDL
   statements as **one** Cloudflare D1 `batch()` against the existing
   database. Verify existing archives/seals unchanged; do not insert a
   `forge_fsa_authority_state` row or open a first-use slot automatically.
5. **Protected original:** only after independently signed owner, selection,
   birth, ledger, start receipt and worker-side lease/epoch fence can the
   existing Windows controller dispatch one actual scientific original,
   verify its result and automatically admit one independent successor.

No Work connector is required. No live D1 mutation, external signer
provisioning, backup export, scientific first use or Windows user account key
generation is performed by adding this source. Existing workflows remain
untouched.
