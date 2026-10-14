# F5 first-use custody — external evidence intake (read-only)

**State:** Engineering source and tests qualified; scientific original **not authorized**. This is an exact request for evidence from the **existing** custodians, not a request to deploy a new FORGE controller/FSA or issue new data.

## Required source of truth

The owner of each existing scientific lane (Wingless and Yggdrasil) must independently attest the **complete seed-use and original-start history from genesis through a specified current high-water**. The custodian, not this F5 candidate, must certify completeness. Include consumed, active and uncertain seed IDs for **both lanes**, every prior started/indeterminate original in the existing `eligibility.LedgerSnapshot`, and externally authenticated high-water floors for **both** lanes. No absent event may be treated as proof of unused status.

The complete record must be signed by an independent Ed25519 custodian whose public key was pinned **out-of-band before** examining the proposed F5 candidate. Use the current `forge.f5.signed-all-lane-seed-custody.v1` schema implemented in `f5custody/verify.go`. The complete signed record must be canonical JSON, and include the `ledger`, three sorted disjoint all-lane seed arrays, both high-water revisions, and the unique monotonically increasing snapshot revision.

Separate independently authenticated pins must supply:
- Custodian Ed25519 public key (32 bytes, lowercase hexadecimal).
- Minimum revision **and** minimum high-water floors for Wingless and Yggdrasil.
- Exact expected `eligibility.LedgerSnapshot` generation and independently pinned ledger SHA256.

**Do not obtain these pins by hashing or copying the same candidate-supplied bundle.** GitHub Actions logs, repo searches, Mind-Palace summaries, fabricated self-signed fixtures and historical successful workflows cannot authenticate them.

## Qualified read-only intake

Only after the original custodian supplies its genuine complete signed bundle, matching independent pins, and a frozen candidate generated from *unconsumed* development and sealed seeds, run:

```text
go run ./cmd/forge-f5-firstuse-audit \
  --candidate <external-frozen-candidate.json> \
  --bundle <external-signed-all-lane-custody.json> \
  --custodian-public-key <independently-pinned-hex-public-key> \
  --minimum-revision <independently-pinned-revision> \
  --wingless-high-water <independently-pinned-wingless-floor> \
  --yggdrasil-high-water <independently-pinned-yggdrasil-floor> \
  --ledger-generation <independently-pinned-generation> \
  --ledger-pin <independently-pinned-ledger-sha256>
```

The inspector is read-only. Even a passing ledger preflight reports `AUDIT_ONLY_SOURCE_AND_ORIGINAL_AUTHORITY_STILL_BLOCKED`: it does not create a first-use claim, select the experiment, freeze scientific evaluation conditions, authorize dispatch or modify a runner.

## Current evidence / exact blockers

- FORGE observer [run 38617698673](https://github.com/spoonman136668-ai/FORGE/actions/runs/38617698673) recorded GitHub metadata with first use **not reconciled**; its 50-run window does not cover complete lane histories.
- CKB-plane wake [run 38619941623](https://github.com/spoonman136668-ai/ckb-plane/actions/runs/38619941623) confirms S10/S11/S14 previously consumed first use; its cursor artifact cannot serve as a complete externally signed seed ledger.
- No actual independent complete signed current all-lane witness, externally pinned Ed25519 key, monotonic revision and lane high-water floors, or accepted prospective F5 seed assignment has been obtained.
- The F5 source content lock pins six qualified source/protocol Git blobs **for engineering only**. New cohort allocation, final scientific preregistration (including blinded evaluator pairs), original source freeze and once-only start authority are still absent.

**Gate result:** `F5_PROSPECTIVE_FIRST_USE=BLOCKED`. Preserve the negative finding. Do not use new seeds merely to move the process forward. No extra paid API, new service or operating controller is required to verify an authentic receipt if the existing custodian can issue it.
