"""V25 exact V20 source-transition tests: synthetic mutation and real cold negatives.

All positive transition mechanics use explicitly patched *synthetic* history.
They are NOT a successful historical V20 owner release. Live owner mutation
remains separately release-pinned and requires original provider ZIP custody.
"""
from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from f139.local_controller import Database, SingleOwner
from f139 import nci04_v25_v20_source_transition as route
from f139.nci04_v24_v20_renewable_readonly_preflight import (
    FROM_V20, FIELDS as PREFLIGHT_FIELDS,
)
from f139.nci04_v25_original_owner_transition_cli import (
    guarded_original_transition,
)
from f139 import nci04_owner_ledger

TARGET = "f" * 40


class OriginalV25IsolatedTransitionTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(prefix="f139-v25-source-migration-")
        self.addCleanup(d.cleanup)
        self.path = Path(d.name) / "synthetic-original.sqlite"
        self.db = Database.initialize(self.path, FROM_V20)
        self.addCleanup(self.db.close)
        self.mutex = self.path.with_suffix(".lock")
        self.db.enable(legacy_suspended=True)
        self.before = self.db.meta().copy()
        self.state = {
            "v20_terminal_event_sha256": "b" * 64,
            "terminal_tasks_sha256": "c" * 64,
            "model_history_sha256": "d" * 64,
            "last_original_free_event_seq": 332,
            "last_original_free_event_sha256": "e" * 64,
            "legacy_free_attempts_spent": 8,
            "verified_historical_tasks": 27,
            "custodied_negative_tasks": 17,
            "custodied_negative_tickets": [
                "f139-nci04-fixture-%03d" % i for i in range(17)],
            "provider_failures_sha256": "a" * 64,
        }
        self.proof = {
            "schema": "forge.f139.nci04.v24.v20-renewable-original-readonly-preflight.v1",
            "from_source_sha": FROM_V20,
            "to_source_sha": TARGET,
            "owner_event_id": 120012,
            "event_seq": self.before["head_seq"],
            "event_head_sha256": self.before["head_hash"],
            **{k:v for k,v in self.state.items()
               if k in PREFLIGHT_FIELDS},
            "verified_tasks": 27, "quarantined_tasks": 17,
            "advisory_only": True, "scientific_first_use": False,
            "production_dispatch_authorized": False,
            "new_controller": False, "new_scheduler": False,
            "new_queue": False, "paid_api_calls": 0,
        }

    def synthetic(self):
        from contextlib import ExitStack
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(
            route, "verify_v24_readonly_preflight",
            return_value={"read_only": True}))
        stack.enter_context(patch.object(route, "_snapshot",
                                       return_value=self.state))
        return stack

    def test_real_cold_original_without_v20_provenance_cannot_transition(self):
        with SingleOwner(self.mutex):
            with self.assertRaises(Exception):
                route.commit_original_v21(
                    self.db, self.proof, owner_witness=lambda: True)
        self.db.verify()
        self.assertEqual(self.before, self.db.meta())
        cold = Database.open_readonly(self.path)
        try:
            self.assertEqual(self.before, cold.meta())
        finally:
            cold.close()

    def test_synthetic_single_event_transaction_is_not_an_owner_receipt(self):
        self.synthetic()
        with SingleOwner(self.mutex), patch.object(self.db, "verify"):
            report = route.commit_original_v21(
                self.db, self.proof, owner_witness=lambda: True)
            self.assertEqual(report["source_sha"], TARGET)
            self.assertEqual(report["event_seq"], self.before["head_seq"]+1)
            self.assertFalse(report["scientific_first_use"])
            self.assertFalse(report["new_controller"])
            self.assertEqual(report["paid_api_calls"], 0)
            rows = list(self.db.conn.execute(
                "SELECT kind,payload FROM events "
                "WHERE kind='SOURCE_TRANSITION_ADMITTED'"))
            self.assertEqual(len(rows), 1)
            import json
            doc = json.loads(rows[0]["payload"])
            self.assertEqual(set(doc), route.FIELDS)
            self.assertEqual(doc["legacy_free_attempts_spent"], 8)
            self.assertEqual(doc["owner_event_id"], self.proof["owner_event_id"])
        # Real cold verifier MUST refuse the synthetic historical predecessor.
        with self.assertRaises(Exception):
            self.db.verify()

    def test_verifier_failure_rolls_back_both_source_and_original_event(self):
        self.synthetic()
        with SingleOwner(self.mutex), patch.object(
                self.db, "verify", side_effect=RuntimeError("injected cold verify")):
            with self.assertRaisesRegex(RuntimeError, "injected cold verify"):
                route.commit_original_v21(
                    self.db, self.proof, owner_witness=lambda: True)
        self.db.verify()
        self.assertEqual(self.db.meta(), self.before)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events "
            "WHERE kind='SOURCE_TRANSITION_ADMITTED'").fetchone()[0], 0)
        cold = Database.open_readonly(self.path)
        try:
            self.assertEqual(cold.meta(), self.before)
        finally:
            cold.close()

    def test_owner_mutex_and_witness_are_explicit_and_non_replayable(self):
        with self.assertRaisesRegex(route.V21TransitionDenied, "MUTEX"):
            route.commit_original_v21(
                self.db, self.proof, owner_witness=lambda: True)
        with SingleOwner(self.mutex):
            with self.assertRaisesRegex(route.V21TransitionDenied, "WITNESS"):
                route.commit_original_v21(
                    self.db, self.proof, owner_witness=lambda: False)
        self.db.verify()
        self.assertEqual(self.db.meta(), self.before)

    def test_v21_cold_schema_rejects_fake_source_and_expansion(self):
        row = {"prior_sha": "a" * 64, "seq": 999}
        fake = {
            "schema": route.SCHEMA, "from_source_sha": FROM_V20,
            "to_source_sha": TARGET, "prior_event_head_sha256": "a"*64,
            "owner_event_id": 1, **self.state,
            "new_dispatches": 0, "scientific_first_use": False,
            "v2_receipt_authorized": False,
        }
        previous = [{"schema": "forge.f139.source-transition.v20",
                     "from_source_sha": "c"*40,
                     "to_source_sha": FROM_V20}]
        with patch.object(route, "_snapshot", return_value=self.state):
            route.verify_v21_cold_source_event(
                self.db, row, fake, previous)
            for change in (
                {"new_dispatches": 1}, {"scientific_first_use": True},
                {"v2_receipt_authorized": True},
                {"owner_event_id": 0},
                {"legacy_free_attempts_spent": 7},
                {"last_original_free_event_sha256": "z"*64},
                {"secret": "forbidden"},
                {"from_source_sha": "a"*40},
            ):
                with self.subTest(change=change), self.assertRaises(
                        route.V21TransitionDenied):
                    route.verify_v21_cold_source_event(
                        self.db, row, {**fake, **change}, previous)

    def test_original_controller_and_native_activation_have_v21_cold_gate(self):
        source = inspect.getsource(Database.verify)
        self.assertIn("is_v21 = (isinstance(doc, dict)", source)
        self.assertIn("verify_v21_cold_source_event(self, row, doc,", source)
        self.assertIn("source_transitions.append(doc)", source)
        self.assertIn('or is_v20 or is_v21', source)
        native = inspect.getsource(nci04_owner_ledger.activate_native)
        self.assertIn('"forge.f139.source-transition.v21"', native)

    def test_windows_one_time_cli_has_no_fallback_on_other_os(self):
        from unittest.mock import patch as mockpatch
        with mockpatch("f139.nci04_v25_original_owner_transition_cli.os.name",
                       "posix"):
            with self.assertRaisesRegex(route.V21TransitionDenied,
                                        "WINDOWS_ORIGINAL_OWNER_ONLY"):
                guarded_original_transition(self.path, self.path)
        self.db.verify()
        self.assertEqual(self.db.meta(), self.before)


if __name__ == "__main__":
    unittest.main()
