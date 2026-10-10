# FORGE FSA R2 — write-once durable checkpoint store primitive

**Status:** FORGE-only source and deterministic synthetic tests. **Not a deployed
independent trust service.** No real scientific authority, FSA signing
credential, off-host trust database, scheduler, controller, broker, research
runner or Mind-Palace writer is provisioned by this change.

## New bounded implementation

`fsaanchorstore.Store` implements the existing `fsatrust.Authority`
interface in a dedicated `forge-fsa-trust` directory, separate from the
`forge-research-archive` and any existing CKB/KTRADE/Mind-Palace
installations. Paths are absolute, checked for forbidden ancestors and
symlinks, and initialized only when the final directory does not exist.

Its genesis anchor must be supplied independently **on every open/restart**:
FORGE-only archive ID, FSA key ID, Ed25519 public key, authority epoch,
sequence zero and genesis digest. No identity is acquired from a local
research worker or the proposed scientific checkpoint.

Every accepted checkpoint is a canonical versioned JSON receipt with
a strictly increasing ordinal, immutable archive/key/epoch identity,
monotonic experiment-record sequence, exact prior receipt SHA-256 and
its own SHA-256. Each sequence filename is exclusively created with
`O_CREATE|O_EXCL`, file-synced and, where supported, directory-synced.
Concurrent attempts against one predecessor cannot both claim success.
After process restart the whole chain is validated rather than silently
skipping a missing/corrupt receipt.

A failed, partial or ambiguous write leaves the original witness intact
and **blocks automatic continuation** until separately qualified
reconciliation. It must not trigger a blind second write or a scientific
experiment replay.

The source-level integration tests exercise the full existing
`fsatrust.Advance` → `fsaanchorstore.Store` →
`privatearchive.Store` path with a synthetic FSA signer, then restart
and read-only `fsatrust.Recover`. No real scientific primary is launched.

## What this explicitly does not prove

- **Not an independent failure domain.** A local directory alone cannot
  resist privileged rollback, whole-directory restoration, deletion of
  a complete trailing receipt, disk corruption, or a compromised host.
  The unit tests explicitly demonstrate a complete-tail deletion can
  cause a locally valid prefix. A genuinely off-host, access-controlled
  and externally witnessed monotonic authority is still mandatory.
- **Not a physical archive proof.** `ConfirmArchiveBinding` matches an
  independently provisioned archive ID; it does not authenticate the
  hardware, volume or specific original archive instance. The remote
  deployment must establish that binding outside the worker's control.
- **Not authorization to call CAS.** This library is an implementation
  primitive; it does not check that its caller is a credentialed FSA
  agent. A deployed private service must authenticate clients, restrict
  writes to authenticated FSA-signed results, and isolate private keys.
- **Not full power-loss atomicity.** Windows directory sync is best-effort,
  because Go's OS interface may not support it. Failure injection in
  CI tests incomplete file handling, not certified physical media
  durability.
- **Not FSA operation.** Historical CKB authorization and KTRADE execution
  privileges never transfer to FORGE. No FORGE research runner, lease or
  scheduler is activated. Mind-Palace is still read-only and advisory.

## Further required gates

Deploy the service under an independently controlled FORGE trust principal
and physically separate durable storage; authenticate operator-provisioned
archive identity, source integrity, client rights and key custody; establish
external immutable witness/checkpoint replication so complete-tail rollback
cannot pass; validate hardware/power-loss and process crash-cuts; qualify
actual Windows native persistence and Linux under races; then test full FSA
scientific acceptance and isolation against concurrently active CKB and
KTRADE controllers before considering controlled activation.

**Non-negotiable:** This source qualifies only a FORGE-native checkpoint
implementation primitive, not a production-ready monotonic authority.
