# F139 V41: source-only offline cold bundle and disposable restore

Development addition to existing V41 backup verification at protected main
f32174255169f907275ddce94c963842db83d3c6. This adds no workflow,
controller, scheduler, installer, owner-task mutation, policy edit, reissue,
release or scientific first-use.

The dormant library stage_offline_cold_bundle requires the pre-existing
query-only original Database and actual SingleOwner mutex, checks original
ledger and complete authenticated source catalog, and creates one exclusively
named run-specific directory. It uses SQLite's online backup API (not unsafe
main-file copying) to include committed WAL state. Reuses existing actual
provider-ZIP and generator-binary source-custody copying. The existing
V41 cold verifier checks hashes, exact original history and every logical
table. A separate disposable SQLite restore is cold-opened, verified and
discarded. A source-hash manifest is written LAST; failures retain an
unsealed non-reusable directory for investigation. It never overwrites a
previous run or stores a credential in receipts.

This is ONLY a development library and test fixture; there is no workflow
invocation/CLI or Windows owner release. The method cannot by itself prove
the original Windows task is stopped and explicitly returns
owner_quiescence_verified=false, source_transition_authorized=false and
release_qualified=false. A separate scoped owner-issued approval, original
task/SID/lease and cold backup/restore acceptance on the real Windows host,
signed release, #1715 once-only disposition, guarded same-task cutover,
post-install readback and native intake acceptance remain mandatory.
Hybrid and scientific first-use stay denied.

Tests use disposable SQLite databases and synthetic history/provider stubs.
Even passing GitHub-hosted Linux/Windows regression is engineering evidence
only, never a release or original-host acceptance.

## Next gate: independently pinned offline restore (no original required)

The *same* dormant helper module now exposes
\`verify_sealed_bundle_offline(folder, expected_manifest_sha256, target, run_id,
expected_head_seq, expected_head_sha256)\`. It is a pure data/backup audit,
not a deployment or Windows maintenance entry point. The four external identity
anchors and root digest must originate in independently authenticated owner
custody; a self-reported manifest is never its own approval.

The verifier re-hashes the canonical sealed manifest and every listed file,
rejects extra files, symlinks, junctions, SQLite sidecars and path escapes,
checks exact provider archive pairs and internal manifest bindings, the sole
previous-generation executable, and the source/ledger head recovered from
an immutable privately hashed SQLite snapshot. It independently restores to
a new disposable SQLite file, re-verifies the chain and all logical tables,
and re-hashes the source bundle on exit. An independently restored file SHA
may differ from the staged SHA at the byte level; logical parity, event-chain
identity and source bundle hashes are the acceptance criteria.

All receipts continue to deny task quiescence, live original-host acceptance,
signed release, source transition, first use, reissue and Hybrid admission.
No workflow or runner is added and the original owner is not contacted.
The additional tests are disposable DEV fixtures only; exact candidate
Linux/Windows qualification and later real owner cold-recovery rehearsal
remain mandatory before deployment.
