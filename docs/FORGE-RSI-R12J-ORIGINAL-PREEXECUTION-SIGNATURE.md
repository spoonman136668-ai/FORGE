# RSI R12-J — independent Ed25519 pre-execution signature verification

Parent protected FORGE main: `84e5e18652f4c8efe4d37e6027fe031c5f1807b0`,
tree `dff2ac346a1315e0a9b0d11f4c885b3be25ef3b8`.
Installed original owner stays at
`42c70d74dd93ef90d0f4618fefefe2206b81eafe`.
Operator owner policy #807 remains Wingless/Yggdrasil only.

## Critical chronology correction

R12-I records a **completed** provider job and cannot authorize that job
to start retroactively. R12-J prepares a distinct **pre-execution**
statement bound to the already-created GitHub run+job (first attempt),
original R11 reservation, R12-G preissue event, protected source/tree,
candidate bytes SHA256, ticket, GitHub owner, and original ledger head.
The original owner would sign this **after dispatch but before worker
execution**. No signer or original owner tick has been wired.

The proof uses Ed25519 detached signatures with a purpose-separated
message domain, and the unmodified Go standard library
`crypto/ed25519.Verify` (Go binary invoked with fixed argv; no network
modules). Tests generate an ephemeral Ed25519 private key in a
short-lived Go test-only process; the private key is never persisted,
printed, or installed and does not become a production trust anchor.
Tests exercise real sign/verify, tampering, forged provider identities,
replay attempt 2, wrong candidate/source and invalid permission fields.
Source qualification includes Linux and Windows.

## Hard trust-root boundary

`f139/rsi_r12j_owner_trust.json` is checked in **disabled** with
`keys=[]`. No private/public production key is enrolled, and no
future operator approval can be implied from successful fixture signing.
`verify_enrolled()` must reject every signature until a separately
approved original-only key is generated/stored outside GitHub and
the corresponding pinned public key is source-qualified. The root
explicitly has `allow_worker_admission=false`. Even after future
public-key enrollment, the pure verifier cannot claim original SQLite
custody, successful single-use original execution claim or scientific
first-use: all these flags remain FALSE.

An authentic original Windows owner still needs a separately authorized
original-only signer/ledger admission, public key custody, a G145-approved
existing-worker workflow release, actual owner source transition, issue
#807 3-lane cutover, and a genuinely fresh eligible failure. This
change does not fabricate any of those. R12-I still only records
completed outcomes. **No original production signing key, secret,
scheduled task, new controller, workflow, runner, queue, deployment,
live dispatch, source promotion or scientific first-use is created.**
