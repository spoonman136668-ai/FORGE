# FORGE R18 — real-original archive metadata anti-ambiguity gate

**Baseline:** FORGE `b20d08eb2cf899349c940a6c03bee18f69af67d4`.

## Concrete defect

`researcharchive.Verify` already binds each public original ZIP to a frozen six-original manifest (repository, GitHub run, attempt, workflow path, source SHA, artifact ID/name, GitHub-reported digest, and content digest). However, its metadata parser delegated JSON directly to Go's `encoding/json`. GitHub run/artifact metadata containing duplicate keys—especially nested `repository.full_name` or `workflow_run.head_sha`—could be accepted with last-write-wins semantics, including case-insensitive aliases that resolve to the same Go struct field. Such ambiguous evidence must never enter a scientific original-custody intake.

## Repair and proof

- Walk every JSON metadata object recursively **before** struct decoding. Reject exact or ASCII-case-equivalent duplicate keys, malformed/trailing JSON, empty/oversized keys, and nesting deeper than 48 levels.
- Add adversarial tests for top-level and nested identity aliases in real-format run/artifact metadata, trailing JSON, and nesting exhaustion. The existing SHA-pinned original ZIP, filename, source and archival classification gates remain intact.
- The six-original read-only workflow now triggers on relevant PRs as well as pushes. In its own Linux job, it fetches original Wingless/Yggdrasil run and artifact metadata plus **the original ZIP bytes**, independently verifies the six pinned source identities and archive digests, and preserves its previous `UNQUALIFIED_ORIGINAL_EVIDENCE_PRESERVED` classifications.
- Require full independent exact-head Linux Go tests/race/vet/build and Windows tests/vet/build **and** a passing exact-PR-head six-original GitHub archive qualification before merge. After merge require post-merge full regression.

## Authority and limits

This gate is an **actual read-only original-artifact intake**, not another synthetic original or scientific proof. GitHub API origin and SHA identities do not establish independent preregistration, source-birth chronology, off-host immutable custody, all-lane consumed first-use, CKB S14 reconciliation, scientific causality or FSA permission. FORGE remains nonexecuting and current Wingless/Yggdrasil research authority unchanged. No paid API, new runner, credentials, original replay or CKB/KTRADE writes.
