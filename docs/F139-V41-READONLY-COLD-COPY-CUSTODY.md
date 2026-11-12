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

INTEGRATION: this candidate incorporates the exact source-transition/schema,
original-source/200-item catalog preflight from PR #1723 and the read-only
unadmitted Yggdrasil #1715 custody/comparator from PR #1724 at their
pinned qualified heads. The only canonical source preflight in this tree is
f139/nci04_v41_catalog_recovery_preflight.py; the older overlapping
nci04_v41_recovery_preflight.py and its tests are deleted. Do not declare
either source PR merged, admit/reissue the pending issue or mutate its remote
identity. Existing nci04_v32_original_owner_transition_cli explicitly
rejects unadmitted native issues, so an operator cannot yet cut over safely.
The V40 release approval is frozen to the wrong predecessor 42c70d74 and
cannot authorize V41. A separate owner-approved, source-qualified transition
must reconcile #1715 without replay or silent dropping before deployment.

This module has no owner approval parser, commit_transition, workflow path,
release ref, or signed first-use issuer. Original owner/task/policy/SQLite
remain unchanged; FSA and Hybrid admission remain denied.

## P1 standalone SQLite backup integrity — blocked until proof

Automated Codex review at PR #1722 HEAD 4a3102df identified that a
state.sqlite-wal file can contain committed state absent from the SHA-256
of state.sqlite; a prior verifier could compare the WAL-augmented logical
view and wrongly attest to the main file alone. This is a source integrity
failure, not a cosmetic or infrastructure-only finding.

The corrected verifier must reject ALL SQLite backup sidecars
(state.sqlite-wal, state.sqlite-shm, state.sqlite-journal), including
dangling symlinks, before reading or hashing the backup and after all
logical archive/custody checks. It must hash the standalone main file
again at the end. Adversarial regressions cover an actual committed
WAL-only table, empty sidecars and main-file alteration after reads.
No source-transition, backup creation, live owner action or science is
authorized by this change. Cold-restore still needs original Windows
acceptance and independently signed owner approval.

## P1 follow-up — immutable main-file verification

The initial strict-sidecar patch at `5c66a3b9...` exposed a valid
SQLite behavior: opening a **standalone** WAL-mode main file with the ordinary
`mode=ro` helper may create a `-shm` sidecar even if no WAL contents were
present at the initial checksum. Its original Linux regression failed
(3 errors/failures in new backup fixture checks), correctly retaining
`ENGINEERING=FAIL` for that SHA. This is not a release candidate.

The successor uses `mode=ro&immutable=1` ONLY for the already-frozen backup,
with query-only mode and the original cold-chain `Database.verify` checks.
That connection never consults or generates WAL/SHM sidecar state, while
the verifier still rejects any pre-existing/new sidecars and rehashes the
main file after parity checks. The **live original** continues using the
existing canonical `Database.open_readonly` under the real kernel mutex;
its behavior and safety are unchanged.

Fixture coverage now also proves a valid standalone WAL-format main file
can be audited without sidecar creation, while an actual uncheckpointed
committed-WAL-only table is rejected. The resulting candidate must pass
all original Linux and Windows regression gates at its exact SHA before
source acceptance.
