"""V41 source-only positive and negative controls; no original owner effects."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from f139 import nci04_v41_recovery_preflight as p


class FakeConn:
    def __init__(self):
        self.query_only = 1
        self.anchor = p.FIRST_OBSERVED_SHA256
        self.terminals = [("VERIFIED", 153), ("QUARANTINED", 56)]
        self.transitions = [{
            "seq": 1463,
            "sha": "a" * 64,
            "payload": json.dumps({
                "schema": "forge.f139.source-transition.v35",
                "from_source_sha": p.PREDECESSOR,
                "to_source_sha": p.FROM,
                "original_head_seq": 1462,
            }),
        }]

    def execute(self, statement, args=()):
        if statement == "PRAGMA query_only":
            return FakeRows([(self.query_only,)])
        if statement.startswith("SELECT sha FROM events WHERE seq="):
            return FakeRows([(self.anchor,)] if args == (p.FIRST_OBSERVED_SEQ,) else [])
        if statement.startswith("SELECT seq,sha,payload FROM events"):
            return FakeRows(self.transitions)
        if statement.startswith("SELECT stage,COUNT(*) FROM tasks"):
            return FakeRows(self.terminals)
        raise AssertionError("unexpected read: " + statement)


class FakeRows:
    def __init__(self, rows):
        self.rows = rows
    def fetchone(self):
        return self.rows[0] if self.rows else None
    def fetchall(self):
        return self.rows


class FakeDB:
    def __init__(self):
        self._readonly_opened = True
        self.conn = FakeConn()
        self.filename = Path("/tmp/f139-v41-unit/state.sqlite")
        self.head = {
            "source_sha": p.FROM,
            "enabled": 1,
            "legacy_suspended": 1,
            "head_seq": 1826,
            "head_hash": p.FIRST_OBSERVED_SHA256,
        }
        self.ready_row = None
        self.active_rows = []
        self.verifications = 0
    def verify(self):
        self.verifications += 1
    def meta(self):
        return dict(self.head)
    def ready(self):
        return self.ready_row
    def actives(self):
        return list(self.active_rows)


class ReadOnlyV41Tests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.target = p.QUALIFIED_REPAIR_MERGE
        self.reads = []
        self.current = self.target
        self.blobs = dict(p.REPAIR_BLOBS)
        self.activated = True

    def get(self, route):
        self.assertTrue(route.startswith("repos/" + p.REPO + "/"))
        self.reads.append(route)
        if route.endswith("/branches/main"):
            return {"protected": True, "commit": {"sha": self.current}}
        for path, sha in self.blobs.items():
            if route.endswith("/contents/" + path + "?ref=" + self.target):
                return {"type": "file", "sha": sha}
        if "/compare/" in route:
            return {"status": "ahead", "ahead_by": 1, "behind_by": 0,
                    "merge_base_commit": {"sha": p.QUALIFIED_REPAIR_MERGE}}
        raise AssertionError("unrecognized original GET: " + route)

    def inspect(self):
        with patch.object(p, "Database", FakeDB), \
             patch.object(p.SingleOwner, "held", return_value=True), \
             patch.object(p, "verify_native_activation", return_value=self.activated), \
             patch.object(p, "prove_deployed_release_pin") as release, \
             patch.object(p, "verify_additional_publication_readback") as ref_only:
            result = p.inspect_original(self.db, self.get, target=self.target)
            release.assert_called_once_with(
                self.get, deployed_source=p.FROM, protected_source=self.target)
            ref_only.assert_called_once_with(self.db, self.get)
            return result

    def denied(self):
        with self.assertRaises(p.RecoveryPreflightDenied):
            self.inspect()

    def test_original_frozen_anchor_and_existing_completed_tasks_succeed(self):
        witness = self.inspect()
        self.assertEqual(witness["head_seq"], 1826)
        self.assertEqual(witness["terminal_verified"], 153)
        self.assertEqual(witness["terminal_quarantined"], 56)
        self.assertEqual(witness["owner_task_sid_and_binary_acceptance"], "NOT_CHECKED")
        self.assertEqual(witness["cold_backup_and_owner_approval"], "NOT_CHECKED")
        self.assertFalse(witness["source_transition_authorized"])
        self.assertFalse(witness["scientific_first_use"])
        self.assertEqual(witness["original_owner_mutations"], 0)
        self.assertEqual(self.db.verifications, 1)
        self.assertTrue(all("?" in r or "/branches/main" in r
                            for r in self.reads))
        self.assertEqual(self.reads.count("repos/" + p.REPO + "/branches/main"), 2)

    def test_growth_of_real_history_and_terminal_tasks_is_not_stale(self):
        self.db.head["head_seq"] = 1900
        self.db.head["head_hash"] = "b" * 64
        self.db.conn.terminals = [("VERIFIED", 155), ("QUARANTINED", 57)]
        w = self.inspect()
        self.assertEqual((w["head_seq"], w["terminal_verified"],
                          w["terminal_quarantined"]), (1900, 155, 57))

    def test_legacy_source_and_activation_are_not_relabelled(self):
        for field, value in (("source_sha", self.target),
                             ("enabled", 0), ("legacy_suspended", 0),
                             ("head_seq", 1825)):
            old = self.db.head[field]
            self.db.head[field] = value
            with self.subTest(field=field):
                self.denied()
            self.db.head[field] = old
        self.activated = False
        self.denied()

    def test_readonly_and_original_mutex_required(self):
        for attribute, value in (("_readonly_opened", False),):
            setattr(self.db, attribute, value)
            self.denied()
            setattr(self.db, attribute, True)
        self.db.conn.query_only = 0
        self.denied()
        self.db.conn.query_only = 1
        with patch.object(p, "Database", FakeDB), \
             patch.object(p.SingleOwner, "held", return_value=False):
            with self.assertRaises(p.RecoveryPreflightDenied):
                p.inspect_original(self.db, self.get, target=self.target)

    def test_original_anchor_cannot_be_replaced(self):
        self.db.conn.anchor = "0" * 64
        self.denied()

    def test_v40_source_transition_must_be_unique_latest_and_authentic(self):
        doc = self.db.conn.transitions[0]
        tests = [
            [],
            [dict(doc), dict(doc)],
            [{**doc, "seq": 1464}],
            [{**doc, "payload": json.dumps({
                "schema": "forge.f139.source-transition.v35",
                "from_source_sha": p.FROM, "to_source_sha": p.PREDECESSOR,
                "original_head_seq": 1462})}],
            [{**doc, "payload": "not-json"}],
        ]
        old = self.db.conn.transitions
        for records in tests:
            self.db.conn.transitions = records
            with self.subTest(records=records), \
                 self.assertRaises(p.RecoveryPreflightDenied):
                self.inspect()
        self.db.conn.transitions = old

    def test_no_pending_or_unknown_stages_are_allowed(self):
        for stages in ([("VERIFIED", 152), ("QUARANTINED", 56)],
                       [("VERIFIED", 153), ("QUARANTINED", 55)],
                       [("VERIFIED", 153), ("QUARANTINED", 56), ("READY", 1)],
                       [("VERIFIED", 153), ("QUARANTINED", 56), ("START_RISK", 1)],
                       [("VERIFIED", 153), ("QUARANTINED", 56), ("WAIT_PROVIDER", 1)]):
            self.db.conn.terminals = stages
            with self.subTest(stages=stages):
                self.denied()
        self.db.conn.terminals = [("VERIFIED", 153), ("QUARANTINED", 56)]
        self.db.ready_row = object()
        self.denied()
        self.db.ready_row = None
        self.db.active_rows = [object()]
        self.denied()

    def test_protected_main_and_repair_blob_custody(self):
        self.current = "0" * 40
        self.denied()
        self.current = self.target
        self.blobs["f139/local_controller.py"] = "0" * 40
        self.denied()

    def test_postmerge_descendants_require_exact_qualified_ancestor(self):
        self.target = "d" * 40
        self.current = self.target
        self.assertEqual(self.inspect()["protected_target_sha"], self.target)
        def wrong_ancestry(route):
            doc = self.get(route)
            if "/compare/" in route:
                doc["merge_base_commit"]["sha"] = "e" * 40
            return doc
        with self.assertRaises(p.RecoveryPreflightDenied):
            p.verify_qualified_repair(wrong_ancestry, self.target)

    def test_invalid_target_and_moving_main_are_denied(self):
        for invalid in (p.FROM, "BAD", "0" * 39, None):
            with self.subTest(invalid=invalid), self.assertRaises(p.RecoveryPreflightDenied):
                p.verify_qualified_repair(self.get, invalid)
        calls = [0]
        def moved(route):
            if route.endswith("/branches/main"):
                calls[0] += 1
                return {"protected": True, "commit": {
                    "sha": self.target if calls[0] == 1 else "0" * 40}}
            return self.get(route)
        with self.assertRaises(p.RecoveryPreflightDenied):
            p.verify_qualified_repair(moved, self.target)

    def test_read_failure_in_custody_proof_is_not_bypassed(self):
        with patch.object(p, "Database", FakeDB), \
             patch.object(p.SingleOwner, "held", return_value=True), \
             patch.object(p, "verify_native_activation", return_value=True), \
             patch.object(p, "prove_deployed_release_pin", side_effect=RuntimeError("offline")):
            with self.assertRaises(RuntimeError):
                p.inspect_original(self.db, self.get, target=self.target)

    def test_original_frozen_read_only_path_never_executes_a_task(self):
        import inspect
        source = inspect.getsource(p)
        for forbidden in ("Disable-ScheduledTask", "Start-ScheduledTask",
                          "db.transition_source(", "db.event(", "db.transaction(",
                          'get("POST"', "create_ref(", "workflow_dispatch("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
