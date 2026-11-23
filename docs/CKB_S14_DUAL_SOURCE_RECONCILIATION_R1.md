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

## R2: exact authenticated CKB issuer wake join

The same CLI now requires a **third** observation: an authenticated GitHub GET for the original S14 CKB owner wake run, selected solely by the `wake_run_id` and `wake_main_sha` inside the independently pinned permanent S14 first-use ledger. No user-provided run-id override or arbitrary GitHub route is accepted.

The wake must belong to `.github/workflows/research-loop-headless-wake-v2.yml` on `main`, with a single original run attempt, `workflow_dispatch` or scheduled trigger, matching original commit, and terminal GitHub run status. A failure is retained as **FAILED_CKB_WAKE_FIRST_USE_STILL_UNRESOLVED_NO_REPLAY**—not evidence that S14 was never consumed. The CKB permanent S14 record is verified again after this network read, blocking changed, deleted or rebound wake identities. Only the fixed CKB GitHub REST API endpoints are allowed, with no redirect following, mutation endpoints, or credential disclosure.

The resulting schema is `forge.ckb.s14-three-source-reconciliation.v1`, with a nested prior two-source report plus the exact CKB wake ID, source SHA, installed controller SHA, terminal outcome and evidence commitment. Every successful report still has `original_replay_authorized=false`, `forge_authority_transferred=false`, `science_activated=false`. This verifies **identity and GitHub terminal metadata**, not the private process failure's root cause, scientific first-use content, genuine worker receipts or final scientific acceptance.

Current independently observed example (for diagnosis only, never a source-of-truth substitute): CKB wake run `38281455598` used `main` source `6b1cc147d34f2dbacdeba13229b725050db74599`, ran as `workflow_dispatch`, attempt 1, and completed **failure** on October 12, 2026. The CLI does not hardcode that run or source; the separately pinned on-disk S14 permanent ledger must authenticate the exact identity.
