# CKB S14 original-run and issuer-intent GitHub reconciliation R1

From an authenticated read-only FORGE work environment with `GH_TOKEN` set to a GitHub token that can **read** the existing `spoonman136668-ai/ckb-plane` workflow records:

```powershell
go run ./cmd/forge-ckb-s14-history
```

The client is **hard-pinned** to GitHub's `api.github.com/repos/spoonman136668-ai/ckb-plane` and performs exactly two authenticated GET requests:

- `/actions/workflows/r216-s14-synthetic-execute.yml/runs?per_page=100`
- `/actions/artifacts?name=ckb-s14-genesis-intent&per_page=100`

It rejects pagination gaps, overfull histories, duplicate JSON keys, incorrect original workflow paths, unexpected run attempts, malformed artifact identities, non-200 responses and untrusted API results. Output records exact original run IDs, signed issuer intent artifact IDs, a deterministic evidence fingerprint, and a **never-replay** classification. HTTP failures cannot become a green observation. No workflow dispatch, rerun endpoint, source mutation or production access exists in this tool.

**Crucial:** An empty GitHub original-run/intent history does **not** establish the original was never consumed: the privately durable CKB `s14-first-use-consumed.v1.json` may already exist from a failed issuer attempt. This GitHub observation is only one side of CKB first-use reconciliation. The CKB S14 wake-run/issuer failure history, its private permanent ledgers and separately authenticated worker/owner receipts still must be jointly reconciled before FORGE can be admitted; any uncertainty blocks activation. No science ran as a result of this diagnostic.
