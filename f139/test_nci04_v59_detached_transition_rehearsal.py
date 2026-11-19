"""V59 detached-copy source-transition authority and negative tests.

No original Windows controller, science workload or owner runner is used.
Synthetic tests are NOT an original-host successful rehearsal receipt.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139 import nci04_v59_detached_transition_rehearsal as v


class FakeConn:
    def __init__(self, readonly: bool):
        self.readonly = readonly
        self.total_changes = 0
        self.database = None

    def execute(self, query, params=()):
        if query == "PRAGMA query_only":
            return self
        if query.startswith("UPDATE meta SET source_sha="):
            self.database._meta["source_sha"] = params[0]
            self.total_changes += 1
            return self
        raise AssertionError("unexpected DB operation: " + query)

    def fetchone(self):
        return (1 if self.readonly else 0,)


class FakeDb:
    def __init__(self, filename: Path, readonly: bool):
        self.filename = filename
        self._readonly_opened = readonly
        self.conn = FakeConn(readonly)
        self.conn.database = self
        self._meta = {
            "schema": "forge.f139.ledger.v1", "source_sha": v.SOURCE,
            "head_seq": v.HEAD_SEQ, "head_hash": v.HEAD_SHA256,
            "enabled": 1, "legacy_suspended": 1,
        }
        self.verified = 0
        self.events = []
        self.txns = 0

    def meta(self):
        return dict(self._meta)

    def verify(self):
        self.verified += 1

    def ready(self):
        return None

    def actives(self):
        return []

    @contextmanager
    def transaction(self):
        self.txns += 1
        yield

    def event(self, name, proof):
        self.events.append(name)
        self._meta["head_seq"] += 1
        self._meta["head_hash"] = "e" * 64

    def close(self):
        return None


class V59DetachedSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.owner = self.root / "original" / "FORGE-F139"
        self.owner.mkdir(parents=True)
        original_path = self.owner / "state.sqlite"
        original_path.write_bytes(b"original-not-touched")
        self.run = v.MIN_OWNER_RUN + 23
        self.sandbox = self.root / "runner-temp"
        self.sandbox.mkdir()
        self.folder = self.sandbox / ("f139-v59-detached-" + str(self.run))
        self.folder.mkdir()
        copy_path = self.folder / "state.sqlite"
        copy_path.write_bytes(b"detached-private-fixture")
        self.original = FakeDb(original_path, True)
        self.copy = FakeDb(copy_path, False)
        self.prior_original = original_path.read_bytes()
        self.patches = [
            patch.object(v, "Database", FakeDb),
            patch.dict(os.environ, {"RUNNER_TEMP": str(self.sandbox)}),
            patch.object(v.SingleOwner, "held", return_value=True),
        ]
        for x in self.patches:
            x.start()
            self.addCleanup(x.stop)
        self.args = dict(target="f"*40, owner_run_id=self.run,
                         qualified_main_run_id=44537056816,
                         rehearsal_run_id=44543045715,
                         backup_sqlite_sha256="a"*64,
                         genenv_executable_sha256="b"*64,
                         generation_mechanism_sha256="c"*64)

    def test_detached_path_exact_and_original_separate(self):
        v.require_detached_paths(self.original, self.copy, self.run)
        self.assertEqual(self.original.conn.total_changes, 0)

    def test_owner_or_copy_cannot_be_writable_original(self):
        self.original._readonly_opened = False
        with self.assertRaisesRegex(v.V59DetachedRehearsalDenied, "CLASS_INVALID"):
            v.require_detached_paths(self.original, self.copy, self.run)
        self.original._readonly_opened = True
        self.copy._readonly_opened = True
        with self.assertRaisesRegex(v.V59DetachedRehearsalDenied, "CLASS_INVALID"):
            v.require_detached_paths(self.original, self.copy, self.run)

    def test_mutation_prohibited_on_untrusted_paths(self):
        before = self.copy.txns
        self.copy.filename = self.original.filename
        with self.assertRaises(v.V59DetachedRehearsalDenied):
            v.rehearse_detached_v48(self.original, self.copy, **self.args)
        self.assertEqual(self.copy.txns, before)
        self.assertEqual(self.original.filename.read_bytes(), self.prior_original)

    def test_reject_unowned_copy_lock_and_missing_runner_root(self):
        with patch.object(v.SingleOwner, "held", return_value=False):
            with self.assertRaisesRegex(v.V59DetachedRehearsalDenied, "MUTEX"):
                v.require_detached_paths(self.original, self.copy, self.run)
        with patch.dict(os.environ, {"RUNNER_TEMP": ""}):
            with self.assertRaisesRegex(v.V59DetachedRehearsalDenied, "RUNNER_ROOT"):
                v.require_detached_paths(self.original, self.copy, self.run)

    def test_reject_unreviewed_target_or_unqualified_hash(self):
        for bad in (v.SOURCE, "g"*40, "f"*39):
            with self.subTest(target=bad):
                with self.assertRaisesRegex(v.V59DetachedRehearsalDenied, "CUSTODY"):
                    v.rehearse_detached_v48(
                        self.original, self.copy,
                        **dict(self.args, target=bad))
        with self.assertRaisesRegex(v.V59DetachedRehearsalDenied, "CUSTODY"):
            v.rehearse_detached_v48(
                self.original, self.copy,
                **dict(self.args, backup_sqlite_sha256="secret"))

    def test_frozen_preimage_required_before_copy_writes(self):
        with patch.object(v, "audit_frozen_original_readonly",
                          side_effect=ValueError("ORIGINAL_OWNER_MISSING")):
            with self.assertRaisesRegex(ValueError, "ORIGINAL_OWNER_MISSING"):
                v.rehearse_detached_v48(
                    self.original, self.copy, **self.args)
        self.assertEqual(self.copy.txns, 0)
        self.assertEqual(self.original.conn.total_changes, 0)

    def test_positive_copy_only_implementation_under_mocked_custody(self):
        # Engineering control-flow test, not a real original owner record.
        before = {
            "source_sha": v.SOURCE, "head_seq": v.HEAD_SEQ,
            "head_sha256": v.HEAD_SHA256, "owner_mutations": 0,
        }
        fields = dict.fromkeys(v.FIELDS, False)
        fields.update({
            "schema": v.SCHEMA, "from_source_sha": v.SOURCE,
            "to_source_sha": self.args["target"],
            "backup_sqlite_sha256": self.args["backup_sqlite_sha256"],
            "owner_run_id": self.args["owner_run_id"],
            "qualified_main_run_id": self.args["qualified_main_run_id"],
            "rehearsal_run_id": self.args["rehearsal_run_id"],
            "genenv_executable_sha256": self.args["genenv_executable_sha256"],
            "generation_mechanism_sha256": self.args["generation_mechanism_sha256"],
            "scientific_first_use": False, "new_dispatches": 0,
            "new_controller": False, "new_scheduler": False, "new_queue": False,
        })
        def activate(copy, approval):
            self.assertIs(copy, self.copy)
            self.assertEqual(approval["source_sha"], self.args["target"])
            self.assertIs(approval["scientific_first_use"], False)
            copy.event("NATIVE_DEVELOPMENT_ACTIVATED", approval)
            return True

        with patch.object(v, "audit_frozen_original_readonly",
                          return_value=before), \
             patch.object(v, "rollback_view", return_value={"rows": 1}), \
             patch.object(v, "_read_copy_proof",
                          return_value=(before, fields,
                                        v.digest(v.canonical({"rows": 1})))), \
             patch.object(v, "activate_native", side_effect=activate), \
             patch.object(v, "verify_native_activation", return_value=True):
            receipt = v.rehearse_detached_v48(
                self.original, self.copy, **self.args)
        self.assertEqual(receipt["detached_event_head_seq"], v.EVENT_SEQ + 1)
        self.assertEqual(receipt["schema"], "forge.f139.v59.detached-v48-rehearsal.v2")
        self.assertEqual(receipt["owner_run_id"], self.run)
        for field in ("qualified_main_run_id", "rehearsal_run_id",
                      "backup_sqlite_sha256", "genenv_executable_sha256",
                      "generation_mechanism_sha256"):
            self.assertEqual(receipt[field], self.args[field])
        self.assertEqual(receipt["original_logical_sha256"],
                         receipt["detached_prewrite_logical_sha256"])
        self.assertEqual(self.copy.meta()["source_sha"], self.args["target"])
        self.assertEqual(self.copy.events,
                         ["SOURCE_TRANSITION_ADMITTED",
                          "NATIVE_DEVELOPMENT_ACTIVATED"])
        self.assertEqual(self.original.meta()["source_sha"], v.SOURCE)
        self.assertEqual(self.original.filename.read_bytes(), self.prior_original)
        self.assertFalse(receipt["source_transition_authorized"])
        self.assertFalse(receipt["scientific_first_use"])

    def test_no_transitions_after_bad_detached_proof(self):
        before = {"source_sha": v.SOURCE,
                  "head_seq": v.HEAD_SEQ,
                  "head_sha256": v.HEAD_SHA256}
        with patch.object(v, "audit_frozen_original_readonly",
                          return_value=before), \
             patch.object(v, "rollback_view", return_value={"rows": 1}), \
             patch.object(v, "_read_copy_proof",
                          return_value=(before, {"bad": True}, "bad")):
            with self.assertRaisesRegex(v.V59DetachedRehearsalDenied,
                                        "PREWRITE_PROOF_INVALID"):
                v.rehearse_detached_v48(
                    self.original, self.copy, **self.args)
        self.assertEqual(self.copy.txns, 0)
        self.assertEqual(self.original.conn.total_changes, 0)


    def test_reject_runner_root_inside_original_owner_tree(self):
        # The old exact-copy-name check could accept RUNNER_TEMP placed under
        # the original FORGE-F139 owner directory. Refuse this before writes.
        inside = self.owner / "injected-runner-temp"
        inside.mkdir()
        folder = inside / ("f139-v59-detached-" + str(self.run))
        folder.mkdir()
        file = folder / "state.sqlite"
        file.write_bytes(b"injected-copy")
        with patch.dict(os.environ, {"RUNNER_TEMP": str(inside)}):
            self.copy.filename = file
            with self.assertRaisesRegex(v.V59DetachedRehearsalDenied,
                                        "ROOT_OVERLAPS_ORIGINAL"):
                v.require_detached_paths(self.original, self.copy, self.run)
        self.assertEqual(self.original.filename.read_bytes(), self.prior_original)

    def test_reject_runner_root_ancestor_of_original_owner(self):
        ancestor = self.root
        folder = ancestor / ("f139-v59-detached-" + str(self.run))
        folder.mkdir()
        file = folder / "state.sqlite"
        file.write_bytes(b"ancestor-copy")
        with patch.dict(os.environ, {"RUNNER_TEMP": str(ancestor)}):
            self.copy.filename = file
            with self.assertRaisesRegex(v.V59DetachedRehearsalDenied,
                                        "ROOT_OVERLAPS_ORIGINAL"):
                v.require_detached_paths(self.original, self.copy, self.run)
        self.assertEqual(self.original.filename.read_bytes(), self.prior_original)

    def test_reject_detached_proof_with_wrong_owner_or_custody_input(self):
        pre = {"source_sha": v.SOURCE, "head_seq": v.HEAD_SEQ,
               "head_sha256": v.HEAD_SHA256}
        bound = dict.fromkeys(v.FIELDS, False)
        bound.update({"schema": v.SCHEMA, "from_source_sha": v.SOURCE,
                      "to_source_sha": self.args["target"],
                      "backup_sqlite_sha256": self.args["backup_sqlite_sha256"],
                      "owner_run_id": self.args["owner_run_id"] + 1})
        with patch.object(v, "audit_frozen_original_readonly", return_value=pre), \
             patch.object(v, "rollback_view", return_value={"rows": 1}), \
             patch.object(v, "_read_copy_proof",
                          return_value=(pre, bound,
                                        v.digest(v.canonical({"rows": 1})))):
            with self.assertRaisesRegex(v.V59DetachedRehearsalDenied,
                                        "PREWRITE_PROOF_INVALID"):
                v.rehearse_detached_v48(self.original, self.copy, **self.args)
        self.assertEqual(self.copy.txns, 0)
        self.assertEqual(self.original.conn.total_changes, 0)

    def test_no_unreviewed_owner_or_task_operations(self):
        source = Path(__file__).with_name(
            "nci04_v59_detached_transition_rehearsal.py").read_text()
        for forbidden in ("Stop-ScheduledTask", "Set-ScheduledTask",
                          "Register-ScheduledTask", "gh api",
                          "sqlite3.connect", "subprocess", "os.system"):
            self.assertNotIn(forbidden, source)
        self.assertIn('"source_transition_authorized": False', source)


if __name__ == "__main__":
    unittest.main()
