# V41 read-only original-owner cold-copy custody qualification

This expands existing draft PR #1722 without adding a second controller, workflow,
scheduler, queue, authorizer, or owner cutover. Original Windows owner evidence
remains [run 43182527036](https://github.com/spoonman136668-ai/FORGE/actions/runs/43182527036):
installed V40 source 2c7caad5..., original ledger head 1826/
71fd4554..., 153 verified, 56 quarantined, zero pending local tasks.
Protected fix PR #1719 is already merged at 7fb1bb9e..., but never installed
into the Windows task.

The new f139/nci04_v41_cold_copy_verifier.py accepts only an externally produced,
canonical run-specific SQLite backup and exact expected SHA-256 under the real
owner kernel mutex. It compares a query-only original against a query-only cold
copy with Database.verify, all-table schema/row digest from the EXISTING
rollback_view, exact current event head, prior source/policy GitHub readback, and
the EXISTING provider-archive and generator-binary custody readers in
copy_files=False mode. No original data, private paths, ledger row contents, or
auth keys are included in the emitted digest-only witness.

The new source-free tests exercise disposable real SQLite database/backups,
valid copy, differing logical table contents, wrong SHA and canonical backup
run identity, altered source metadata, symlink, absent original mutex, writeable
original handle, and lost provider/generator custody. These tests are NOT
original-Windows acceptance.

IMPORTANT: PR #1723 independently implements overlapping original-source
and exact-200 catalog preflights; PR #1724 independently qualifies unadmitted
Yggdrasil #1715. Do not declare either merged/admitted or duplicate its
remote issue. Existing nci04_v32_original_owner_transition_cli explicitly
rejects unadmitted native issues, so an operator cannot yet cut over safely.
The V40 release approval is frozen to the wrong predecessor 42c70d74 and
cannot authorize V41. A separate owner-approved, source-qualified transition
must reconcile #1715 without replay or silent dropping before deployment.

This module has no owner approval parser, commit_transition, workflow path,
release ref, or signed first-use issuer. Original owner/task/policy/SQLite
remain unchanged; FSA and Hybrid admission remain denied.
