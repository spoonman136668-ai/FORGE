"""DEV-only V41 #1715 escrow grammar and negative controls."""
from contextlib import closing
from pathlib import Path
import tempfile
import sqlite3
import unittest
from f139.nci04_native_contract import canonical
from f139 import nci04_v41_pending_escrow as escrow
from f139.local_controller import Database

class V41EscrowTests(unittest.TestCase):
    def document(self):
        return dict(schema=escrow.SCHEMA, source_sha=escrow.OWNER_SOURCE,
            issue_number=1715, issue_id=6333201763,
            ticket="f139-nci04-i1715-"+escrow.OWNER_SOURCE[:12]+"-12345678",
            issue_body_sha256="a"*64, native_intent_sha256="b"*64,
            semantic_identity_sha256="c"*64, target_commit="d"*40,
            target_tree_sha="e"*40,
            original_head_seq=escrow.OBSERVED_SEQ,
            original_head_sha256="f"*64,
            frozen_observed_seq=escrow.OBSERVED_SEQ,
            frozen_observed_head_sha256=escrow.OBSERVED_HEAD,
            owner_comment_id=777, owner_comment_body_sha256="a"*64,
            pending_disposition="EXPLICIT_ESCROW_ONCE", new_dispatches=0,
            reissue_authorized=False, scientific_first_use=False,
            hybrid_admission=False)

    def row(self):
        return {"seq":escrow.OBSERVED_SEQ+1, "prior_sha":"f"*64}

    def test_exact_event_grammar(self):
        self.assertTrue(escrow.verify_event_shape(self.row(), self.document()))

    def test_no_dispatch_or_mutation_authority(self):
        import inspect
        source=inspect.getsource(escrow)
        for forbidden in ("db.event(", "workflow_dispatch(", "db.transition_source(",
                          "Start-ScheduledTask", "create_ref(", ".post("):
            self.assertNotIn(forbidden, source)
        self.assertFalse(hasattr(escrow,"commit_escrow"))

    def test_malformed_and_replay_fields_rejected(self):
        changes = [
            {"schema":"wrong"}, {"source_sha":"0"*40},
            {"issue_number":True}, {"issue_number":1714},
            {"issue_id":1}, {"issue_id":True}, {"ticket":"wrong"},
            {"issue_body_sha256":"bad"}, {"native_intent_sha256":"bad"},
            {"target_commit":"bad"}, {"target_tree_sha":"bad"},
            {"original_head_seq":escrow.OBSERVED_SEQ+1},
            {"original_head_sha256":"0"*64},
            {"frozen_observed_seq":1}, {"frozen_observed_head_sha256":"0"*64},
            {"owner_comment_id":0}, {"owner_comment_id":True},
            {"owner_comment_body_sha256":"bad"},
            {"pending_disposition":"REISSUE"}, {"new_dispatches":1},
            {"new_dispatches":True}, {"reissue_authorized":True},
            {"scientific_first_use":True}, {"hybrid_admission":True},
            {"extraneous":True},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(escrow.EscrowDenied):
                escrow.verify_event_shape(self.row(), {**self.document(),**change})
        with self.assertRaises(escrow.EscrowDenied):
            escrow.verify_event_shape(
                {"seq":escrow.OBSERVED_SEQ,"prior_sha":"f"*64},self.document())

    def synthetic_cold_events(self):
        # Minimal synthetic SQL table proves escrow replay predicates only.
        # It is NOT a substitute for the authentic original SHA-chain.
        conn=sqlite3.connect(":memory:", isolation_level=None)
        conn.row_factory=sqlite3.Row
        conn.executescript(
            "CREATE TABLE events(seq INTEGER PRIMARY KEY, kind TEXT, sha TEXT, "
            "prior_sha TEXT, payload TEXT);"
            "CREATE TABLE tasks(ticket TEXT);"
        )
        conn.execute(
            "INSERT INTO events VALUES(?,?,?,?,?)",
            (escrow.OBSERVED_SEQ,"OTHER_EVENT",escrow.OBSERVED_HEAD,"0"*64,"{}"))
        conn.execute(
            "INSERT INTO events VALUES(?,?,?,?,?)",
            (escrow.OBSERVED_SEQ+1,escrow.KIND,"1"*64,"f"*64,
             canonical(self.document()).decode("ascii")))
        return conn

    def test_synthetic_adjacent_escrow_and_replay_guards(self):
        class Cold:
            def __init__(self, conn):
                self.conn=conn
        with closing(self.synthetic_cold_events()) as conn:
            db=Cold(conn)
            self.assertEqual(
                escrow.verify_before_transition(db,escrow.OBSERVED_SEQ+2),
                "1"*64)
            with self.assertRaisesRegex(escrow.EscrowDenied, "NONADJACENT"):
                escrow.verify_before_transition(db,escrow.OBSERVED_SEQ+3)
            conn.execute(
                "INSERT INTO events VALUES(?,?,?,?,?)",
                (escrow.OBSERVED_SEQ+2,escrow.KIND,"2"*64,"1"*64,
                 canonical(self.document()).decode("ascii")))
            with self.assertRaisesRegex(escrow.EscrowDenied, "DUPLICATE"):
                escrow.verify_before_transition(db,escrow.OBSERVED_SEQ+2)
            conn.execute("DELETE FROM events WHERE seq=?",
                         (escrow.OBSERVED_SEQ+2,))
            conn.execute("UPDATE events SET sha=? WHERE seq=?",
                         ("9"*64,escrow.OBSERVED_SEQ))
            with self.assertRaisesRegex(escrow.EscrowDenied, "FROZEN_PREFIX"):
                escrow.verify_before_transition(db,escrow.OBSERVED_SEQ+2)
            conn.execute("UPDATE events SET sha=? WHERE seq=?",
                         (escrow.OBSERVED_HEAD,escrow.OBSERVED_SEQ))
            conn.execute(
                "INSERT INTO events VALUES(?,?,?,?,?)",
                (escrow.OBSERVED_SEQ-1,"NATIVE_DEVELOPMENT_ADMITTED",
                 "e"*64,"d"*64,'{"issue_number":1715}'))
            with self.assertRaisesRegex(escrow.EscrowDenied, "ALREADY_ADMITTED"):
                escrow.verify_before_transition(db,escrow.OBSERVED_SEQ+2)
            conn.execute("DELETE FROM events WHERE seq=?",
                         (escrow.OBSERVED_SEQ-1,))
            conn.execute("INSERT INTO tasks VALUES(?)",
                         (self.document()["ticket"],))
            with self.assertRaisesRegex(escrow.EscrowDenied, "TASK_ALREADY_PRESENT"):
                escrow.verify_before_transition(db,escrow.OBSERVED_SEQ+2)


    def test_orphan_must_not_survive_cold_reopen(self):
        """Committed orphan, unrelated successor and fake V41 pairing all fail."""
        from unittest.mock import patch
        from f139.local_controller import SingleOwner

        class Synthetic:
            def __init__(self, conn):
                self.conn = conn
                self.filename = Path("synthetic-copy.sqlite")
                self._readonly_opened = False
            def meta(self):
                latest = self.conn.execute(
                    "SELECT seq,sha,kind,payload FROM events ORDER BY seq DESC LIMIT 1"
                ).fetchone()
                source_sha = escrow.OWNER_SOURCE
                if latest["kind"] == "SOURCE_TRANSITION_ADMITTED":
                    source_sha = __import__("json").loads(
                        latest["payload"])["to_source_sha"]
                return {"source_sha": source_sha,
                        "head_seq": latest["seq"], "head_hash": latest["sha"]}

        with closing(self.synthetic_cold_events()) as conn:
            db = Synthetic(conn)
            with self.assertRaisesRegex(escrow.EscrowDenied,
                                        "COMMITTED_OR_UNOWNED_ORPHAN"):
                escrow.audit_committed_escrow(db)
            conn.execute("BEGIN IMMEDIATE")
            try:
                with self.assertRaisesRegex(escrow.EscrowDenied,
                                            "COMMITTED_OR_UNOWNED_ORPHAN"):
                    escrow.audit_committed_escrow(db)
                with patch.object(SingleOwner,"held",return_value=True):
                    self.assertEqual(escrow.audit_committed_escrow(db),
                                     "PROVISIONAL_OWNER_TRANSACTION")
                    conn.execute("INSERT INTO events VALUES(?,?,?,?,?)",
                        (escrow.OBSERVED_SEQ+2, "OTHER_EVENT",
                         "2"*64, "1"*64, "{}"))
                    with self.assertRaisesRegex(escrow.EscrowDenied,
                                                "NONADJACENT_OR_WRONG_SUCCESSOR"):
                        escrow.audit_committed_escrow(db)
            finally:
                conn.execute("ROLLBACK")
            valid = dict(schema="forge.f139.source-transition.v36",
                from_source_sha=escrow.OWNER_SOURCE,
                to_source_sha="9"*40,
                original_head_seq=escrow.OBSERVED_SEQ+1,
                prior_event_head_sha256="1"*64,
                pending_1715_escrow_sha256="1"*64,
                owner_event_id=777)
            conn.execute("INSERT INTO events VALUES(?,?,?,?,?)",
                (escrow.OBSERVED_SEQ+2,"SOURCE_TRANSITION_ADMITTED",
                 "2"*64, "1"*64,canonical(valid).decode("ascii")))
            self.assertEqual(escrow.audit_committed_escrow(db),
                             "PAIRED_V41_TRANSITION")
            wrong={**valid, "owner_event_id":778}
            conn.execute("UPDATE events SET payload=? WHERE seq=?",
                (canonical(wrong).decode("ascii"),escrow.OBSERVED_SEQ+2))
            with self.assertRaisesRegex(escrow.EscrowDenied,
                                        "SOURCE_PAIR_IDENTITY_DRIFT"):
                escrow.audit_committed_escrow(db)
            conn.execute("UPDATE events SET payload=? WHERE seq=?",
                (canonical(valid).decode("ascii"),escrow.OBSERVED_SEQ+2))
            conn.execute("INSERT INTO events VALUES(?,?,?,?,?)",
                (escrow.OBSERVED_SEQ+3,escrow.KIND,
                 "3"*64,"2"*64,canonical(self.document()).decode("ascii")))
            with self.assertRaisesRegex(escrow.EscrowDenied,"MULTIPLE_ESCROWS"):
                escrow.audit_committed_escrow(db)

    def test_empty_original_denied_without_sqlite_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            dbpath=Path(folder)/"state.sqlite"
            with closing(Database.initialize(dbpath,escrow.OWNER_SOURCE)) as db:
                old=db.meta().copy()
                with self.assertRaises(escrow.EscrowDenied):
                    escrow.verify_before_transition(db,escrow.OBSERVED_SEQ+2)
                self.assertEqual(db.meta(),old)

if __name__ == "__main__":
    unittest.main()
