"""DEV-only V41 #1715 escrow grammar and negative controls."""
from contextlib import closing
from pathlib import Path
import tempfile
import sqlite3
import unittest
from f139.local_controller import canonical as event_canonical
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
             event_canonical(self.document()).decode("ascii")))
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
                 event_canonical(self.document()).decode("ascii")))
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


    def test_owner_event_writer_bytes_and_noncanonical_negatives(self):
        # The genuine Database.event writer appends a newline to every payload.
        # The escrow-specific verifier must use that exact grammar, not the
        # distinct newline-free native intent hashing canonicalization.
        import json
        with closing(self.synthetic_cold_events()) as conn:
            payload = conn.execute(
                "SELECT payload FROM events WHERE kind=?", (escrow.KIND,)
            ).fetchone()["payload"]
            self.assertEqual(payload, event_canonical(self.document()).decode("ascii"))
            self.assertTrue(payload.endswith("\n"))
            class Cold:
                def __init__(self, db):
                    self.conn = db
            db = Cold(conn)
            self.assertEqual(escrow.verify_before_transition(
                db, escrow.OBSERVED_SEQ + 2), "1" * 64)
            for bad in (payload[:-1],
                        json.dumps(self.document(), indent=2) + "\n",
                        payload + "\n"):
                with self.subTest(bad_length=len(bad)):
                    conn.execute("UPDATE events SET payload=? WHERE kind=?",
                                 (bad, escrow.KIND))
                    with self.assertRaisesRegex(
                            escrow.EscrowDenied, "ESCROW_NONCANONICAL"):
                        escrow.verify_before_transition(
                            db, escrow.OBSERVED_SEQ + 2)
            conn.execute("UPDATE events SET payload=? WHERE kind=?",
                         (payload, escrow.KIND))
            self.assertEqual(escrow.verify_before_transition(
                db, escrow.OBSERVED_SEQ + 2), "1" * 64)

    def test_actual_database_event_uses_accepted_escrow_bytes(self):
        # Synthetic high-water mark tests the REAL Database.event serializer,
        # not authenticity of the historical original SHA-chain.
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "copy.sqlite"
            with closing(Database.initialize(path, escrow.OWNER_SOURCE)) as db:
                db.conn.execute(
                    "UPDATE meta SET head_seq=?,head_hash=? WHERE id=1",
                    (escrow.OBSERVED_SEQ, "f" * 64))
                db.event(escrow.KIND, self.document())
                row = db.conn.execute(
                    "SELECT payload FROM events WHERE kind=?", (escrow.KIND,)
                ).fetchone()
                self.assertEqual(row["payload"],
                                 event_canonical(self.document()).decode("ascii"))
                # Missing synthetic frozen history must still be denied, but
                # the event's canonical encoding is valid.
                with self.assertRaisesRegex(
                        escrow.EscrowDenied, "FROZEN_PREFIX_DRIFT"):
                    escrow.verify_before_transition(
                        db, escrow.OBSERVED_SEQ + 2)

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
                 "2"*64, "1"*64,event_canonical(valid).decode("ascii")))
            self.assertEqual(escrow.audit_committed_escrow(db),
                             "PAIRED_V41_TRANSITION")
            wrong={**valid, "owner_event_id":778}
            conn.execute("UPDATE events SET payload=? WHERE seq=?",
                (event_canonical(wrong).decode("ascii"),escrow.OBSERVED_SEQ+2))
            with self.assertRaisesRegex(escrow.EscrowDenied,
                                        "SOURCE_PAIR_IDENTITY_DRIFT"):
                escrow.audit_committed_escrow(db)
            conn.execute("UPDATE events SET payload=? WHERE seq=?",
                (event_canonical(valid).decode("ascii"),escrow.OBSERVED_SEQ+2))
            conn.execute("INSERT INTO events VALUES(?,?,?,?,?)",
                (escrow.OBSERVED_SEQ+3,escrow.KIND,
                 "3"*64,"2"*64,event_canonical(self.document()).decode("ascii")))
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

    def test_paired_escrow_catalog_exclusion_preserves_old_identity(self):
        # Synthetic pairing only: the real owner revalidates full SQLite
        # custody and each issue/target through the existing GitHub catalog.
        import json

        class Catalog:
            def __init__(self, conn, source):
                self.conn, self.source = conn, source
            def meta(self):
                return {"source_sha": self.source}

        target_source = "9" * 40
        historical = {1700: (1, escrow.OWNER_SOURCE, "a" * 64, "old-ticket")}
        with closing(self.synthetic_cold_events()) as conn:
            db = Catalog(conn, target_source)
            with self.assertRaisesRegex(escrow.EscrowDenied,
                                        "COMMITTED_OR_UNOWNED_ORPHAN"):
                escrow.catalog_escrow_exclusion(db, historical, target_source)
            successor = dict(
                schema="forge.f139.source-transition.v36",
                from_source_sha=escrow.OWNER_SOURCE,
                to_source_sha=target_source,
                original_head_seq=escrow.OBSERVED_SEQ+1,
                prior_event_head_sha256="1"*64,
                pending_1715_escrow_sha256="1"*64,
                owner_event_id=777)
            conn.execute("INSERT INTO events VALUES(?,?,?,?,?)",
                (escrow.OBSERVED_SEQ+2, "SOURCE_TRANSITION_ADMITTED",
                 "2"*64, "1"*64, event_canonical(successor).decode("ascii")))
            before = conn.total_changes
            actual = escrow.catalog_escrow_exclusion(
                db, historical, target_source)
            original = self.document()
            self.assertEqual(set(actual), {1700, 1715})
            self.assertEqual(actual[1700], historical[1700])
            self.assertEqual(actual[1715], (
                original["issue_id"], escrow.OWNER_SOURCE,
                original["issue_body_sha256"], original["ticket"]))
            self.assertNotIn(1715, historical)  # Never mutate caller's record
            self.assertEqual(conn.total_changes, before)

            with self.assertRaisesRegex(escrow.EscrowDenied,
                                        "CATALOG_ESCROW_ALREADY_ADMITTED"):
                escrow.catalog_escrow_exclusion(
                    db, {**historical, 1715: actual[1715]}, target_source)
            with self.assertRaisesRegex(escrow.EscrowDenied,
                                        "CATALOG_SOURCE_OR_PAIR_DRIFT"):
                escrow.catalog_escrow_exclusion(
                    db, historical, escrow.OWNER_SOURCE)
            conn.execute("INSERT INTO tasks VALUES(?)",
                         (original["ticket"],))
            with self.assertRaisesRegex(escrow.EscrowDenied,
                                        "CATALOG_ESCROW_HAS_TASK"):
                escrow.catalog_escrow_exclusion(db, historical, target_source)
            conn.execute("DELETE FROM tasks")
            conn.execute("UPDATE events SET payload=? WHERE seq=?",
                (event_canonical({**successor, "owner_event_id": 778}).decode("ascii"),
                 escrow.OBSERVED_SEQ+2))
            with self.assertRaisesRegex(escrow.EscrowDenied,
                                        "SOURCE_PAIR_IDENTITY_DRIFT"):
                escrow.catalog_escrow_exclusion(db, historical, target_source)

    def test_without_escrow_catalog_does_not_excuse_stale_issues(self):
        class Catalog:
            def __init__(self, conn):
                self.conn = conn
        with closing(self.synthetic_cold_events()) as conn:
            conn.execute("DELETE FROM events WHERE kind=?", (escrow.KIND,))
            db = Catalog(conn)
            old = {1700: (1, escrow.OWNER_SOURCE, "a"*64, "old-ticket")}
            before = conn.total_changes
            self.assertIs(escrow.catalog_escrow_exclusion(
                db, old, "9"*40), old)
            self.assertEqual(conn.total_changes, before)

    def test_escrowed_native_candidate_never_auto_reissued(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from f139.local_controller import GitHub
        from f139.nci04_autonomy_feed import candidate_identity

        with closing(self.synthetic_cold_events()) as conn:
            class Catalog:
                def __init__(self, connection, source):
                    self.conn, self.source = connection, source
                def meta(self):
                    return {"source_sha": self.source}
            source = "9" * 40
            db = Catalog(conn, source)
            successor = dict(
                schema="forge.f139.source-transition.v36",
                from_source_sha=escrow.OWNER_SOURCE,
                to_source_sha=source,
                original_head_seq=escrow.OBSERVED_SEQ+1,
                prior_event_head_sha256="1"*64,
                pending_1715_escrow_sha256="1"*64,
                owner_event_id=777)
            conn.execute("INSERT INTO events VALUES(?,?,?,?,?)",
                (escrow.OBSERVED_SEQ+2, "SOURCE_TRANSITION_ADMITTED",
                 "2"*64, "1"*64, event_canonical(successor).decode("ascii")))
            frozen = self.document()
            candidate = SimpleNamespace(
                target_commit=frozen["target_commit"],
                target_tree_sha=frozen["target_tree_sha"],
                path="yggdrasil/public_causal_cells.py",
                after_sha256="f"*64)
            original = SimpleNamespace(
                number=1715, issue_id=frozen["issue_id"],
                source_sha=escrow.OWNER_SOURCE,
                ticket=frozen["ticket"],
                issue_body_sha256=frozen["issue_body_sha256"],
                native_intent_sha256=frozen["native_intent_sha256"],
                lane="Yggdrasil", candidate=candidate)
            api = GitHub()
            historical = escrow.catalog_escrow_exclusion(db, {}, source)
            oldchanges = conn.total_changes
            with patch("f139.nci04_v41_pending_custody._authenticated_remote_issue",
                       return_value=original) as read, patch(
                       "f139.nci04_v41_pending_custody._semantic_identity",
                       return_value=frozen["semantic_identity_sha256"]) as semantic:
                identity = escrow.escrowed_native_candidate_identity(
                    db, api, historical, source)
                self.assertEqual(identity, candidate_identity(
                    "Yggdrasil", candidate.target_commit,
                    candidate.path, candidate.after_sha256))
                self.assertEqual(conn.total_changes, oldchanges)
                self.assertEqual(set(historical), {1715})
                read.assert_called_once_with(api, 1715, escrow.OWNER_SOURCE)
                with self.assertRaisesRegex(
                        escrow.EscrowDenied, "FEED_ESCROW_CATALOG_DRIFT"):
                    escrow.escrowed_native_candidate_identity(
                        db, api, {}, source)
                semantic.assert_called_once()
                read.return_value = SimpleNamespace(**{
                    **vars(original), "issue_body_sha256": "0"*64})
                with self.assertRaisesRegex(
                        escrow.EscrowDenied, "FEED_CANDIDATE_CUSTODY_DRIFT"):
                    escrow.escrowed_native_candidate_identity(
                        db, api, historical, source)
                read.return_value = original
                semantic.return_value = "0"*64
                with self.assertRaisesRegex(
                        escrow.EscrowDenied, "FEED_CANDIDATE_CUSTODY_DRIFT"):
                    escrow.escrowed_native_candidate_identity(
                        db, api, historical, source)
            with self.assertRaisesRegex(
                    escrow.EscrowDenied, "FEED_SOURCE_OR_PAIR_DRIFT"):
                escrow.escrowed_native_candidate_identity(
                    db, api, historical, escrow.OWNER_SOURCE)

    def test_escrowless_autofeed_requires_no_remote_reads(self):
        from unittest.mock import patch
        with closing(self.synthetic_cold_events()) as conn:
            conn.execute("DELETE FROM events WHERE kind=?", (escrow.KIND,))
            class Catalog:
                def __init__(self, connection):
                    self.conn = connection
            db = Catalog(conn)
            with patch("f139.nci04_v41_pending_custody._authenticated_remote_issue",
                       side_effect=AssertionError("unexpected remote call")):
                self.assertIsNone(escrow.escrowed_native_candidate_identity(
                    db, None, {}, "9"*40))

if __name__ == "__main__":
    unittest.main()
