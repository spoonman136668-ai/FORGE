"""Disposable SQLite transaction tests: never an original Windows owner."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139 import nci04_v41_atomic_copy_rehearsal as atomic
from f139 import nci04_v41_owner_approval as approval
from f139 import nci04_v41_pending_custody as pending
from f139 import nci04_v41_source_transition as source
from f139 import nci04_v41_pending_escrow as escrow

SOURCE = escrow.OWNER_SOURCE
TARGET = "9" * 40
HEAD = "f" * 64

def cold_receipt():
    return dict(
        schema="forge.f139.v41.original-owner-cold-copy-readonly.v1",
        source_sha=SOURCE, candidate_sha=TARGET,
        original_head_seq=escrow.OBSERVED_SEQ,
        original_head_sha256=HEAD,
        backup_sha256="a"*64, verified_isolated_snapshot_sha256="a"*64,
        logical_all_tables_sha256="b"*64,
        provider_archives_manifest_sha256="c"*64,
        generation_binary_manifest_sha256="d"*64,
        preserved_verified_tasks=153, preserved_quarantined_tasks=56,
        original_owner_mutations=0, source_transition_authorized=False,
        new_dispatches=0, scientific_first_use=False, hybrid_admission=False)

def preserved():
    return dict(schema=pending.SCHEMA, source_sha=SOURCE,
        original_head_seq=escrow.OBSERVED_SEQ,
        original_head_sha256=HEAD, issue_number=1715,
        issue_id=6333201763,
        ticket="f139-nci04-i1715-"+SOURCE[:12]+"-aabbccdd",
        issue_body_sha256="a"*64, native_intent_sha256="b"*64,
        target_commit="c"*40, target_tree_sha="d"*40,
        semantic_identity_sha256="e"*64,
        disposition="UNADMITTED_RETAINED_NO_DISPATCH",
        source_transition_authorized=False,
        reissue_authorized=False, new_dispatches=0,
        owner_mutations=0, scientific_first_use=False)

def owner_intent():
    return dict(schema=approval.RECEIPT,
        original_source_sha=SOURCE, target_source_sha=TARGET,
        owner_comment_id=123456,
        owner_comment_body_sha256="f"*64,
        original_head_seq=escrow.OBSERVED_SEQ,
        original_head_sha256=HEAD,
        pending_issue_number=1715,
        pending_disposition_requested="EXPLICIT_ESCROW_ONCE",
        pending_disposition_implemented=False,
        original_owner_release_qualified=False,
        owner_comment_identity_verified=True, provider_reads_only=True,
        remote_writes=0, owner_mutations=0, new_dispatches=0,
        source_transition_authorized=False, reissue_authorized=False,
        scientific_first_use=False, hybrid_admission=False)

def synthetic_proof(db, target, event_id, binary_sha, toolchain):
    # Simulate the authentic full-history proof ONLY; the transaction and
    # SQL rollback are real. See v41 source tests for actual proof grammar.
    m = db.meta()
    return dict({field:None for field in source.FIELDS},
        schema=source.SCHEMA, from_source_sha=SOURCE,
        to_source_sha=target, owner_event_id=event_id,
        original_head_seq=m["head_seq"],
        prior_event_head_sha256=m["head_hash"],
        pending_1715_escrow_sha256=m["head_hash"])

class AtomicCopiedLedgerTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.original=Path(self.folder.name)/"original.sqlite"
        self.copy=Path(self.folder.name)/"copied.sqlite"
        with closing(Database.initialize(self.original,SOURCE)) as db:
            # Synthetic high-water is deliberately NOT authentic old history.
            # Db.verify is mocked ONLY in these transaction-focused tests.
            db.conn.execute(
                "UPDATE meta SET enabled=1,legacy_suspended=1,"
                "head_seq=?,head_hash=? WHERE id=1",
                (escrow.OBSERVED_SEQ,HEAD))
            self.start=db.meta()
            with closing(sqlite3.connect(str(self.copy))) as out:
                db.conn.backup(out)

    def execute(self, failure=None, mutate=None, lock_copy=True, same=False):
        from contextlib import ExitStack
        with patch.object(Database,"verify",return_value=None), \
                patch.object(source,"build_proof",side_effect=synthetic_proof):
            with closing(Database(self.copy)) as db:
                with ExitStack() as stack:
                    stack.enter_context(SingleOwner(self.original.with_suffix(".lock")))
                    if lock_copy:
                        stack.enter_context(SingleOwner(self.copy.with_suffix(".lock")))
                    cold, pending_receipt, owner = cold_receipt(), preserved(), owner_intent()
                    if mutate:
                        mutate(cold, pending_receipt, owner)
                    return atomic._atomic_on_copy(
                        db, original_path=self.copy if same else self.original,
                        original_meta=self.start, target=TARGET,
                        binary_sha="7"*64, toolchain=source.TOOLCHAIN,
                        cold_receipt=cold, pending_receipt=pending_receipt,
                        owner_intent=owner, inject_failure=failure)

    def state(self, path):
        with closing(sqlite3.connect(str(path))) as db:
            return (db.execute("SELECT source_sha,head_seq,head_hash FROM meta"
                               ).fetchone(),
                    db.execute("SELECT seq,kind,sha FROM events ORDER BY seq"
                               ).fetchall())

    def test_one_commit_writes_escrow_then_transition_to_copy_only(self):
        original=self.state(self.original)
        result=self.execute()
        self.assertEqual(result["copy_head_seq"],escrow.OBSERVED_SEQ+2)
        self.assertFalse(result["source_transition_authorized"])
        self.assertEqual(self.state(self.original),original)
        meta,events=self.state(self.copy)
        self.assertEqual(meta[0],TARGET)
        self.assertEqual(meta[1],escrow.OBSERVED_SEQ+2)
        self.assertEqual([x[1] for x in events],
                         [escrow.KIND,"SOURCE_TRANSITION_ADMITTED"])
        self.assertEqual(result["escrow_event_sha256"],events[0][2])
        with self.assertRaisesRegex(atomic.V41AtomicDenied,
                                    "COPY_PREIMAGE_MOVED"):
            self.execute()

    def test_faults_rollback_both_events_and_source(self):
        initial=self.state(self.copy)
        original=self.state(self.original)
        for fault in ("after_escrow","after_source_event","after_verify"):
            with self.subTest(fault=fault):
                with self.assertRaisesRegex(atomic.V41AtomicDenied,"INJECTED"):
                    self.execute(failure=fault)
                self.assertEqual(self.state(self.copy),initial)
                self.assertEqual(self.state(self.original),original)

    def test_lock_custody_and_approval_are_fail_closed(self):
        original=self.state(self.original)
        for opts in (dict(lock_copy=False),dict(same=True),
                     dict(mutate=lambda c,p,o:o.update(
                         source_transition_authorized=True)),
                     dict(mutate=lambda c,p,o:o.update(
                         pending_disposition_requested="REISSUE")),
                     dict(mutate=lambda c,p,o:p.update(issue_number=1714)),
                     dict(mutate=lambda c,p,o:c.update(
                         backup_sha256="0"*64))):
            with self.subTest(opts=str(opts)):
                with self.assertRaises((atomic.V41AtomicDenied,
                                        approval.V41ApprovalDenied)):
                    self.execute(**opts)
                self.assertEqual(self.state(self.original),original)
                self.assertEqual(self.state(self.copy),original)

    def test_original_must_be_query_only_and_no_live_commands(self):
        with patch.object(Database,"verify",return_value=None):
            with closing(Database(self.original)) as db:
                with self.assertRaises(atomic.V41AtomicDenied):
                    atomic.rehearse_locked_original(
                        db,self.copy,None,None,target=TARGET,
                        qualification_run_id=1,backup_sha256="0"*64,
                        owner_comment_id=1,copy_path=self.copy.with_name(
                            "third.sqlite"),binary_sha="7"*64,
                        toolchain=source.TOOLCHAIN)
        import inspect
        code=inspect.getsource(atomic)
        for forbidden in ("workflow_dispatch(", "Start-ScheduledTask",
                          "Disable-ScheduledTask", ".post(", "git push",
                          "create_ref("):
            self.assertNotIn(forbidden,code)

if __name__ == "__main__":
    unittest.main()
