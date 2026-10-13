# FORGE witnessed shadow-recovery pipeline R1

This is an **actual executable integration path** across the previously developed components—not merely another standalone diagnosis helper. The command verifies BOTH original Wingless/Yggdrasil lane identities, independent source observations and separately signed complete failure reviews, builds a hash-chained incident archive, writes a sealed recovery manifest, stages *only* qualified pre-first-use reversible repair candidates into the existing inactive content-addressed recovery outbox, and writes a human-readable machine-verifiable report. Restart verification re-authenticates the stored evidence against independently supplied pins and checks the entire chain, classification and outbox content.

Usage (example, from the FORGE repo):

```powershell
go run ./cmd/forge-shadow-recover --request C:\forge-safe\pinned-input.json --root C:\forge-safe\forge-shadow-recovery
go run ./cmd/forge-shadow-recover --verify --request C:\forge-safe\pinned-input.json --root C:\forge-safe\forge-shadow-recovery
```

Input JSON schema `forge.shadow.pipeline-input.v1` contains `witness_pins`, `witnesses`, `reviewer_pins`, `reviews`. Each pin has a 64-character lowercase `public_key_hex`; witness pins also include `lane`, `existing_lane_id`, `existing_queue_id`, `source_repo`, `source_commit_sha`, `owner_id`, `owner_epoch`, `journal_head_sha256`, and `minimum_observation_sequence`. Reviewer pins specify `lane` and `minimum_review_sequence`. The signed claims and findings use the existing Go JSON wire fields from `lanewitness.Signed` and `lanereview.SignedFinding`. No private key belongs in this file.

The command always uses the actual clock for freshness; it does not trust user-supplied clock fields. Every run writes to a *new*, exclusively created `forge-shadow-recovery` directory. Existing, partially written or crash-ambiguous batches are never overwritten. `--verify` is read-only and requires externally pinned keys and identities. No incident means no bogus success artifact. It never edits CKB, historical scientific evidence, acceptance refs, KTRADE, or original experiment first-use ledgers.

**Authority boundary:** operator pins must come from an independently qualified trust channel. This code proves signature validity relative to those pins; it cannot prove real-world collector reliability or that external raw evidence was truthful. Local file syncing is not an off-host linearizable authority or verified power-loss durability. No scientific runner, code-repair executor, original retry, owner grant, task lease, controller swap, cutover or autonomous-science acceptance is provided. Every report explicitly records **zero verified scientific cycles**. CKB-plane remains the only active authority over the original research lanes until a separately qualified and approved cutover.
