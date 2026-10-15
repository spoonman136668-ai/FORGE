# FORGE R20A — historical preregistration source-binding (2026-10-15)

**Disposition: SOURCE-ONLY PARTIAL; SCIENTIFIC CUSTODY UNQUALIFIED.**

R19 already independently reconstructed six authentic historical ZIPs in the existing protected D1 (3 Wingless, 3 Yggdrasil). R20A adds a narrowly bounded, read-only observation of their corresponding frozen research-source Git blobs. The exact six original HEADs, original GitHub workflow/run/artifact and original ZIP SHA-256 remain fixed in `reference/research-originals/20261013-six-recent-archive-cohort.json`.

Using exact immutable **original experiment commit SHAs** via the connected GitHub repository API, R20A observed the following preregistration paths/blobs. Blob SHA is the **Git object SHA-1**, not a SHA-256 preregistration digest and not an independent source-birth witness:

| Lane / Original | Preregistration path in source commit | Git blob SHA-1 |
|---|---|---|
| Wingless W-R24 | `research/contrib/chatgpt/20261013-w-r24-missingness/pre.json` | `b31bf89b5f0e4300a36592ffacc97a6dac5a5edc` |
| Wingless W-R25 | `research/contrib/chatgpt/20261013-w-r25-alignment/prereg.json` | `0b430e6f701f939ca13e1899c8d937418c21a262` |
| Wingless W-R26 | `research/contrib/chatgpt/20261013-w-r26-next-prediction/prereg.json` | `708e05de6725d9a0fe6ab3f69eced46b9de5790b` |
| Yggdrasil Y037 | `research/contrib/chatgpt/20261013-y037-diversity/pre.json` | `538f0e70a0be350f71b73ab9f5106679cf27fb5f` |
| Yggdrasil Y038 | `research/contrib/chatgpt/20261013-y038-retention-capacity/prereg.json` | `e6ee97bef29ce53bfe30f20ddccac3e61fc910af` |
| Yggdrasil Y039 | `research/contrib/chatgpt/20261013-y039-interrupt/prereg.json` | `cfeffae76c60f08d9781fbba4904b4d69ea461f5` |

Machine-readable pins and explicit **false** authority fields: `reference/research-originals/20261015-r20-prereg-source-observations.json`. `researcharchive/r20_source_pins_test.go` checks lane, unique experiment, frozen source SHA, prereg file path/blob structure and rejects any attempt to mark independently witnessed birth, first-use reconciliation or scientific acceptance true.

**Still unproven:** third-party timestamped source origin/freeze, independent source-birth signer/key custody, complete consumed first-use ledger and monotonic high-water (including legacy CKB owner state), external first-use attestation, and separately trusted cross-host exactly-once control. Historical source commits and now-archived ZIPs cannot supply these missing facts by inference. Do not rerun six consumed originals, generate synthetic signers, declare optimizer improvement, or dispatch/pro-mote scientific experiments from this record.

**Next R20B:** obtain and verify an existing *independently protected* source-birth and consumed-first-use evidence channel against all six pinned identities. Reuse existing `sourcebirth.Verify`, `ckbcustody`, and `optimizerbridge` read-only verification interfaces. If signatures/high-water are unavailable, return **UNQUALIFIED**, keep the six ZIPs for historical context only, and advance new prospective hypotheses only through the existing authorized scientific owner. No new scheduler, Worker, D1, paid API, Cloudflare mutation or research loop changes.
