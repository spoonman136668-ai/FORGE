# Original CKB first-use migration inventory (read-only)

`go run ./cmd/forge-ckb-custody --state C:\ProgramData\CKBR\research\state --pinned C:\forge-safe\ckb-firstuse-pins.json`

Implements a **concrete read-only adapter** to the original CKB-plane irreversible first-use ledgers for S09, S10, S11, S12, S13, and optionally S14. The authoritative reference schemas and pinned prereg Git objects are taken from `research/successor-builder/s71_s14_evidence.py` and `s72_s14_oneuse_issuer.py` in CKB-plane. Nothing is automatically collected or authenticated merely because it is local.

The adapter verifies each historical ledger is canonical JSON, with unique keys, exact generation/schema, consumed-state semantics and `replay_authorized=false`; it verifies S12/S13/S14 preregistration Git blob identities and, if S14 exists, all five predecessor ledger SHA256 hashes, original wake/controller provenance, and KTRADE/broker/production isolation. Missing S09-S13 records, corrupt bodies, symlinks or predecessor drift fail closed. Absent S14 is explicitly **ABSENT_OR_UNKNOWN_NO_REPLAY**—never proof of unused first-use.

A separately provisioned `--pinned` file is REQUIRED. It must be canonical compact JSON followed by a newline:
```json
{"schema":"forge.ckb.pinned-firstuse-hashes.v1","sha256":{"S09":"<64 lowercase hex>","S10":"<64 lowercase hex>","S11":"<64 lowercase hex>","S12":"<64 lowercase hex>","S13":"<64 lowercase hex>"}}
```
Include S14 only if its authenticated ledger exists. The report exposes only generation, filename, SHA256, an inventory commitment, and a conservative no-replay classification—not raw sensitive state. The command cannot write to the CKB state directory, stop the legacy controller, activate FORGE, create research lanes, or launch a scientific original.

**Qualification gap:** The immutable hashes must come from a separate authenticated, up-to-date CKB owner/witness source. This inspector only confirms byte matches to those externally pinned hashes. It does not prove an off-host witness is trustworthy, reconcile GitHub Actions first-use/intent histories, or establish independent FORGE ownership. Explicit approved qualified cutover remains mandatory.
