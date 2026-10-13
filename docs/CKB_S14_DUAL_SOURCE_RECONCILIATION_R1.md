# Read-only CKB S14 two-source first-use reconciliation

Use an authenticated Windows session with **read-only** GitHub Actions access and independently acquired, authenticated SHA256 pins for all six original permanent CKB first-use generations:

```powershell
go run ./cmd/forge-ckb-s14-reconcile --state C:\\ProgramData\\CKBR\\research\\state --pinned C:\\forge-safe\\ckb-firstuse-pins.json
```

`GH_TOKEN` must be configured securely in the process environment; the command neither prints nor writes it. Pin input is canonical compact JSON, followed by a newline:
```json
{"schema":"forge.ckb.pinned-firstuse-hashes.v1","sha256":{"S09":"<64 lowercase hex>","S10":"<64 lowercase hex>","S11":"<64 lowercase hex>","S12":"<64 lowercase hex>","S13":"<64 lowercase hex>","S14":"<64 lowercase hex>"}}
```

The integration reads and independently verifies the original S09–S14 permanent first-use ledgers, consults the existing CKB S14 original GitHub workflow and intent-artifact inventories, and **re-reads the original local custody** to reject changes during network inspection. It reports consumed-first-use, original attempt IDs, issuer artifact IDs, provenance commitments, missing evidence and exact remaining blockers. GitHub emptiness **never** clears local consumed first-use. Absent or ambiguous local S14, changed pins, truncated workflow histories, invalid GitHub signatures/metadata, source drift or network failure blocks.

This is an executable read-only integration, not a controller. A success is `READ_ONLY_CKB_S14_CONSUMED_NO_REPLAY`, `cutover_authorized=false`, `original_replay_authorized=false`, with zero independently verified scientific cycles. The known S74 original-issuer wake failure still requires CKB private wake-run and ledger reconciliation before any independent FORGE control. Original Wingless/Yggdrasil scientific results, including negative results, stay with CKB until qualified authority transfer. KTRADE remains untouched and paper-only.
