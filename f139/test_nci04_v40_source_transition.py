"""Three-epoch source-contract qualification; fixtures are not live custody."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139 import nci04_v40_source_transition as route
from f139 import nci04_v39_source_transition as prior
from f139 import nci04_partial_publication_custody as custody
from f139 import nci04_v40_original_owner_transition_cli as cli
from f139 import nci04_v38_original_owner_transition_cli as shared_cli
from f139 import test_nci04_v39_source_transition as prior_tests
from f139.local_controller import Database, SingleOwner


class V40SuccessorTests(unittest.TestCase):
    def history(self):
        # Extend the existing three-source custody fixture; never load an
        # original owner DB, archive, private source, HMAC or scientific episode.
        fixture = prior_tests.V39Tests()
        self.addCleanup(fixture.doCleanups)
        db, row, previous = fixture.history()
        state = fixture.snapshot(db, row, previous)
        v39 = {**fixture.document(state), "to_source_sha": route.FROM_V39}
        db.conn.execute("INSERT INTO events VALUES(?,?,?,?,?)",
            (1309, "SOURCE_TRANSITION_ADMITTED", "d"*64, "a"*64, json.dumps(v39)))
        db.conn.execute("INSERT INTO events VALUES(?,?,?,?,?)",
            (1310, "NATIVE_DEVELOPMENT_ACTIVATED", "a"*64, "d"*64, "{}"))
        seq = 1311
        for index in range(17):
            identity = hashlib.sha256(str(index).encode()).hexdigest()
            attempt = {**custody.original_payload(), "candidate_identity": identity,
                "source_after_sha256": identity, "source_sha": route.FROM_V39,
                "branch": "f139/auto-model-y-"+identity[:20]+"-992ef142aaa5"}
            success = dict(schema=custody.PUBLICATION, candidate_identity=identity,
                source_after_sha256=identity, pr_number=1100+index, head_commit="b"*40,
                scientific_first_use=False, worker_dispatched=False)
            for kind, doc in (("MODEL_DRAFT_ATTEMPTED", attempt),
                              ("MODEL_DRAFT_AUTHENTICATED", success)):
                db.conn.execute("INSERT INTO events VALUES(?,?,?,?,?)",
                    (seq, kind, "a"*64, "a"*64, json.dumps(doc)))
                seq += 1
            if index < 16:
                db.conn.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
                    ("v39-positive-"+str(index), "VERIFIED", 5100+index, "a"*64,
                     "/fixture", route.FROM_V39, "Yggdrasil", None, None, None))
        for number in range(seq, route.MIN_HEAD+1):
            db.conn.execute("INSERT INTO events VALUES(?,?,?,?,?)",
                (number, "FIXTURE_PREFIX_PADDING", "a"*64, "a"*64, "{}"))
        return db, dict(seq=route.MIN_HEAD+1, prior_sha="a"*64), previous+[v39]

    def snapshot(self, db, row, previous):
        with patch.object(route, "g54_original_canonical", return_value={"ticket": "fixture-g54"}):
            return route.snapshot(db, row, previous)

    def document(self, state):
        return dict(schema=route.SCHEMA, from_source_sha=route.FROM_V39,
            to_source_sha="e"*40, owner_event_id=123,
            prior_event_head_sha256="a"*64, original_head_seq=route.MIN_HEAD,
            **state, genenv_executable_sha256="b"*64, genenv_toolchain=route.TOOLCHAIN,
            generation_mechanism_sha256="c"*64, new_dispatches=0,
            scientific_first_use=False, v2_receipt_authorized=False,
            purpose="three-lane-development-source-handoff",
            qualified_worker_blob=route.QUALIFIED_WORKER_BLOB)

    def test_three_epoch_growth_and_frozen_negative_survive_cold_contract_replay(self):
        db, row, previous = self.history()
        state = self.snapshot(db, row, previous)
        self.assertEqual(state["verified_historical_tasks"], 113)
        self.assertEqual(state["custodied_negative_tasks"], 56)
        self.assertEqual(state["preserved_counters"]["MODEL_DRAFT_ATTEMPTED"], 127)
        self.assertEqual(state["preserved_counters"]["MODEL_DRAFT_AUTHENTICATED"], 126)
        self.assertEqual(state["partial_publication_custody"], custody.custody_packet())
        self.assertEqual(state["v39_transition_sha256"], "d"*64)
        before = db.conn.total_changes
        with patch.object(route, "g54_original_canonical", return_value={"ticket": "fixture-g54"}):
            route.verify_cold_event(db, row, self.document(state), previous)
        self.assertEqual(db.conn.total_changes, before)
        # The old two-epoch parser must continue to refuse current-source growth.
        with self.assertRaises(custody.PartialPublicationDenied):
            custody.validate_retained(db, row["seq"], 1240,
                "3dd63467d649a347692b6b42cd5074ff1038d3de",
                successor_boundary=1305, successor_source=prior.FROM_V38)

    def test_missing_ack_extra_pending_attempt_and_epoch_tamper_fail_closed(self):
        db, row, previous = self.history()
        attempt = json.loads(db.conn.execute("SELECT payload FROM events WHERE seq=1311").fetchone()[0])
        faults = (
            ("DELETE FROM events WHERE seq=1312", ()),
            ("UPDATE events SET payload=? WHERE seq=1311", (json.dumps({**attempt, "source_sha": prior.FROM_V38}),)),
            ("UPDATE events SET payload=? WHERE seq=1307", (json.dumps({**attempt, "source_sha": route.FROM_V39}),)),
            ("UPDATE events SET sha='bad' WHERE seq=1309", ()),
            ("UPDATE events SET sha='bad' WHERE seq=1305", ()),
            ("UPDATE tasks SET stage='READY' WHERE ticket='v39-positive-0'", ()),
            ("DELETE FROM tasks WHERE ticket=?", (route.I1464_TICKET,)),
        )
        for statement, args in faults:
            with self.subTest(statement=statement):
                db.conn.execute("SAVEPOINT fault")
                db.conn.execute(statement, args)
                try:
                    with self.assertRaises(route.MaintenanceDenied):
                        state = self.snapshot(db, row, previous)
                        with patch.object(route, "g54_original_canonical", return_value={"ticket": "fixture-g54"}):
                            route.verify_cold_event(db, row, self.document(state), previous)
                finally:
                    db.conn.execute("ROLLBACK TO fault")
                    db.conn.execute("RELEASE fault")

    def test_exact_predecessor_worker_identity_replay_and_counter_fences(self):
        db, row, previous = self.history()
        state = self.snapshot(db, row, previous)
        doc = self.document(state)
        for change in ({"from_source_sha": prior.FROM_V38}, {"schema": prior.SCHEMA},
                       {"to_source_sha": route.FROM_V39}, {"owner_event_id": True},
                       {"qualified_worker_blob": "0"*40}, {"scientific_first_use": True},
                       {"new_dispatches": 1}, {"v2_receipt_authorized": True},
                       {"history_sha256": "0"*64}, {"v39_transition_sha256": "0"*64},
                       {"preserved_counters": {}}, {"extra": False}):
            with self.subTest(change=change), patch.object(route, "snapshot", return_value=state):
                with self.assertRaises(route.MaintenanceDenied):
                    route.verify_cold_event(db, row, {**doc, **change}, previous)
        for chain in ([], previous+[previous[-1]], previous+[doc],
                      [{**previous[-1], "from_source_sha": "0"*40}]):
            with self.subTest(chain=chain), self.assertRaises(route.MaintenanceDenied):
                route.verify_cold_event(db, row, doc, chain)

    def test_third_epoch_requires_both_exact_seals_and_strict_boundaries(self):
        db, row, previous = self.history()
        base = dict(successor_boundary=1305, successor_source=prior.FROM_V38,
                    second_successor_boundary=1309, second_successor_source=route.FROM_V39)
        for change in ({"successor_boundary": None}, {"second_successor_boundary": True},
                       {"second_successor_boundary": 1305}, {"second_successor_boundary": row["seq"]},
                       {"second_successor_source": "f"*40}, {"successor_source": "f"*40}):
            with self.subTest(change=change), self.assertRaises(custody.PartialPublicationDenied):
                custody.validate_retained(db, row["seq"], 1240,
                    "3dd63467d649a347692b6b42cd5074ff1038d3de", **{**base, **change})

    def test_postverify_failure_rolls_back_real_sqlite_meta_and_event(self):
        with tempfile.TemporaryDirectory() as tmp, closing(Database.initialize(
                Path(tmp)/"state.sqlite", route.FROM_V39)) as db:
            before = db.meta().copy()
            proof = {key: None for key in route.FIELDS}
            proof["to_source_sha"] = "e"*40
            with SingleOwner(db.filename.with_suffix(".lock")):
                with patch.object(route, "build_proof", return_value=proof), \
                     patch.object(db, "verify", side_effect=ValueError("cold verification failed")):
                    with self.assertRaisesRegex(ValueError, "cold verification failed"):
                        route.commit_transition(db, proof, owner_witness=lambda: True)
            self.assertEqual(db.meta(), before)
            db.verify()
        with self.assertRaises(route.MaintenanceDenied):
            route.readonly_snapshot(None)

    def test_cli_live_mode_fails_before_git_database_or_owner_operations(self):
        with patch.object(cli.subprocess, "check_output") as git, patch.object(cli, "shared_main") as run:
            for argv in ([], ["--db", "unused", "--target", "e"*40],
                         ["--preflight-only", "--verify-pretransition-rollback"]):
                with self.subTest(argv=argv), self.assertRaisesRegex(route.MaintenanceDenied, "LIVE_MIGRATION_NOT_AUTHORIZED"):
                    cli.main(argv)
            git.assert_not_called()
            run.assert_not_called()
        self.assertIs(shared_cli.selected_contract(route), route)
        # Calling the shared CLI directly cannot bypass the V40 read-only
        # wrapper: the existing live handoff does not register this contract.
        with self.assertRaisesRegex(ValueError, "UNKNOWN_SOURCE_CONTRACT"):
            shared_cli.main(["--db", "unused", "--target", "e"*40,
                "--backup", "unused", "--event-id", "1", "--genenv-executable", "unused",
                "--genenv-toolchain", route.TOOLCHAIN], _contract=route)

    def test_cli_dirty_source_wrong_target_and_wrong_worker_deny_before_database(self):
        for values in (("e"*40, "dirty"), ("f"*40,), ("e"*40, "", "0"*40)):
            with self.subTest(values=values), patch.object(cli.subprocess, "check_output", side_effect=values), \
                    patch.object(cli, "shared_main") as run:
                with self.assertRaises(route.MaintenanceDenied):
                    cli.main(["--preflight-only", "--db", "unused", "--target", "e"*40])
                run.assert_not_called()

    def test_readonly_missing_mutex_or_unqualified_original_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"state.sqlite"
            with closing(Database.initialize(path, route.FROM_V39)) as db:
                before = db.meta().copy()
            with closing(Database.open_readonly(path)) as readonly:
                with self.assertRaises(route.MaintenanceDenied):
                    route.readonly_snapshot(readonly)
                with SingleOwner(path.with_suffix(".lock")):
                    with self.assertRaises(route.MaintenanceDenied):
                        route.readonly_snapshot(readonly)
                self.assertEqual(readonly.meta(), before)
                self.assertEqual(readonly.conn.total_changes, 0)
                self.assertEqual(readonly.conn.execute("PRAGMA query_only").fetchone()[0], 1)

    def test_modern_release_guard_requires_exact_v35_fields_and_existing_native_custody(self):
        from f139.local_controller import v2_owner_terminal_release_guard
        db, row, previous = self.history()
        doc = self.document(self.snapshot(db, row, previous))
        with tempfile.TemporaryDirectory() as tmp, closing(Database.initialize(
                Path(tmp)/"state.sqlite", "e"*40)) as owner:
            owner.enable(legacy_suspended=True)
            owner.event("SOURCE_TRANSITION_ADMITTED", doc)
            # Only the adapter is isolated here; full historical cryptographic
            # replay is required separately and is not proven by this fixture.
            with patch.object(owner, "verify"), patch("f139.local_controller.g54_original_canonical"), \
                    patch("f139.nci04_g49_prepost_negative.verify_g49_custody", return_value=True), \
                    patch("f139.nci04_owner_ledger.verify_native_activation", return_value=True):
                self.assertTrue(v2_owner_terminal_release_guard("e"*40, owner))
                owner.event("SOURCE_TRANSITION_ADMITTED", {**doc, "v2_receipt_authorized": True})
                self.assertFalse(v2_owner_terminal_release_guard("e"*40, owner))

    def test_binary_adapter_binds_exact_v35_worker_and_source_fields(self):
        import sqlite3
        from types import SimpleNamespace
        from f139 import nci04_genenv_owner_backend as backend
        from f139.nci04_native_contract import digest
        db, row, previous = self.history()
        doc = self.document(self.snapshot(db, row, previous))
        with tempfile.TemporaryDirectory() as tmp:
            raw = b"source-only custody fixture; never executed"
            binary = Path(tmp)/"genenv-source"/("e"*40)/"f139-genenv-source.exe"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(raw)
            conn = sqlite3.connect(":memory:")
            self.addCleanup(conn.close)
            conn.row_factory = sqlite3.Row
            conn.execute("CREATE TABLE events(seq INTEGER,kind TEXT,payload TEXT)")
            doc["genenv_executable_sha256"] = digest(raw)
            doc["generation_mechanism_sha256"] = digest(backend.generation_mechanism())
            conn.execute("INSERT INTO events VALUES(?,?,?)", (1, "SOURCE_TRANSITION_ADMITTED", json.dumps(doc)))
            original = SimpleNamespace(conn=conn, filename=Path(tmp)/"state.sqlite",
                verify=lambda: None, meta=lambda: {"source_sha": "e"*40})
            self.assertEqual(backend.executable_custody(original, "e"*40), (binary, digest(raw)))
            backend.typed_generation_custody(original, "e"*40, doc["generation_mechanism_sha256"])
            for change in ({"qualified_worker_blob": "0"*40}, {"from_source_sha": prior.FROM_V38}):
                conn.execute("UPDATE events SET payload=?", (json.dumps({**doc, **change}),))
                with self.assertRaises(backend.BackendUnavailable):
                    backend.executable_custody(original, "e"*40)
                with self.assertRaises(backend.BackendUnavailable):
                    backend.typed_generation_custody(original, "e"*40, doc["generation_mechanism_sha256"])


if __name__ == "__main__":
    unittest.main()
