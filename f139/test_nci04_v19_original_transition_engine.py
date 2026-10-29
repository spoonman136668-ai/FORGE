"""Source-only V19 original transition: isolated synthetic SQLite and mocks.

Not a release/cutover rehearsal. Historical V18 custody is NOT fabricated as
real acceptance: the synthetic test patches DB.verify and owner-attestation
dependencies solely to exercise transaction construction and rollback.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_negative_owner_store import TICKET as FIRST, SOURCE_SHA as FIRST_SOURCE
from f139.nci04_split_negative_owner_store import TICKET as SECOND, SOURCE as SECOND_SOURCE
from f139.nci04_g49_prepost_negative import TICKET as PREPOST, SOURCE_V7
from f139.nci04_v19_original_release_readonly_preflight import SOURCE as V18

TARGET = "a" * 40
NEW_SCHEMA = "forge.f139.source-transition.v19"


class V19IsolatedEngineTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory(prefix="f139-v19-transition-isolated-")
        self.addCleanup(td.cleanup)
        self.path = Path(td.name) / "original-fixture.sqlite"
        self.db = Database.initialize(self.path, V18)
        self.addCleanup(self.db.close)
        self.db.enable(legacy_suspended=True)
        self.g54 = "f139-nci04-g54-synthetic-test"
        self.provider = "f139-nci04-provider-synthetic-test"
        self.recognized = {
            FIRST: FIRST_SOURCE,
            SECOND: SECOND_SOURCE,
            PREPOST: SOURCE_V7,
            self.g54: "b" * 40,
            self.provider: "c" * 40,
        }
        for index in range(24):
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,"
                "manifest_sha,run_id,evidence_dir,evidence_sha) "
                "VALUES(?,?,?,'VERIFIED',?,?,?,?)",
                (f"f139-nci04-v19-fixture-{index:03d}", "Wingless", V18,
                 "a" * 64, index + 1, "/fixture-only", "b" * 64))
        for ticket, source in self.recognized.items():
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) "
                "VALUES(?,?,?,'QUARANTINED',?)",
                (ticket, "Yggdrasil", source, "c" * 64))
        # These are NOT authenticated model events; actual verification is
        # deliberately patched below, not silently assumed.
        historical = {
            "G3_DRAFT_ATTEMPTED": 1, "G3_DRAFT_AUTHENTICATED": 1,
            "MODEL_DRAFT_ATTEMPTED": 3, "MODEL_DRAFT_AUTHENTICATED": 3,
            "FREE_REASONER_ATTEMPTED": 2,
        }
        for kind, count in historical.items():
            for i in range(count):
                self.db.event(kind, {"synthetic": True, "sequence": i})
        self.db.event("SOURCE_TRANSITION_ADMITTED", {
            "schema": "forge.f139.source-transition.v18",
            "from_source_sha": "d" * 40, "to_source_sha": V18,
            "synthetic_not_authentic": True,
        })
        self.before = self.db.meta().copy()

    def harness(self):
        from contextlib import ExitStack
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(self.db, "verify"))
        stack.enter_context(patch.object(
            self.db, "verified_native_provider_failures",
            return_value={self.provider: ("c" * 40, "e" * 64)}))
        stack.enter_context(patch(
            "f139.local_controller.g54_original_canonical",
            return_value={"ticket": self.g54, "source_sha": "b" * 40}))
        for name, result in (
            ("f139.nci04_negative_owner_store.verify_original_negative_custody", True),
            ("f139.nci04_split_negative_owner_store.verify_second_negative_custody", True),
            ("f139.nci04_g49_prepost_negative.verify_g49_custody", True),
            ("f139.nci04_owner_ledger.verify_native_activation", True),
        ):
            stack.enter_context(patch(name, return_value=result))
        return stack

    def transition(self, **options):
        return self.db.transition_source(
            TARGET, allow_certified_negative=True, **options)

    def v19_events(self):
        return [json.loads(row["payload"]) for row in self.db.conn.execute(
            "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
            if json.loads(row["payload"]).get("schema") == NEW_SCHEMA]

    def test_v19_requires_explicit_flag_and_existing_owner_mutex(self):
        self.harness()
        with self.assertRaisesRegex(Exception, "V19_ORIGINAL_MUTEX_REQUIRED"):
            self.transition(allow_v19=True)
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaisesRegex(Exception, "V19_EXPLICIT_OPT_IN_REQUIRED"):
                self.transition()
        self.assertEqual(self.db.meta(), self.before)
        self.assertEqual(self.v19_events(), [])

    def test_bounded_single_event_has_prior_v18_seal_and_no_science_authority(self):
        self.harness()
        v18_row = self.db.conn.execute(
            "SELECT sha FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        with SingleOwner(self.path.with_suffix(".lock")):
            self.transition(allow_v19=True)
        self.assertEqual(self.db.meta()["source_sha"], TARGET)
        self.assertEqual(self.db.meta()["head_seq"], self.before["head_seq"] + 1)
        self.assertEqual(len(self.v19_events()), 1)
        doc = self.v19_events()[0]
        self.assertEqual(doc["from_source_sha"], V18)
        self.assertEqual(doc["to_source_sha"], TARGET)
        self.assertEqual(doc["v18_terminal_event_sha256"], v18_row["sha"])
        self.assertEqual(doc["custodied_negative_tasks"], 5)
        self.assertEqual(doc["verified_historical_tasks"], 24)
        self.assertFalse(doc["v2_receipt_authorized"])
        self.assertFalse(doc["scientific_first_use"])
        self.assertEqual(doc["new_dispatches"], 0)
        for name in ("terminal_tasks_sha256", "model_history_sha256",
                     "provider_failures_sha256"):
            self.assertRegex(doc[name], r"^[0-9a-f]{64}$")

    def test_duplicate_or_changed_owner_source_denied_without_second_event(self):
        self.harness()
        with SingleOwner(self.path.with_suffix(".lock")):
            self.transition(allow_v19=True)
            after = self.db.meta().copy()
            with self.assertRaises(Exception):
                self.transition(allow_v19=True)
        self.assertEqual(self.db.meta(), after)
        self.assertEqual(len(self.v19_events()), 1)

    def test_failed_post_append_validation_rolls_back_all_source_and_event(self):
        self.harness()
        with SingleOwner(self.path.with_suffix(".lock")):
            calls = []
            def verify():
                calls.append(1)
                if len(calls) == 2:
                    raise RuntimeError("INJECTED_COLD_CHECK_FAILURE")
            with patch.object(self.db, "verify", side_effect=verify):
                with self.assertRaisesRegex(RuntimeError, "INJECTED_COLD_CHECK_FAILURE"):
                    self.transition(allow_v19=True)
        self.assertEqual(self.db.meta(), self.before)
        self.assertEqual(self.v19_events(), [])

    def test_ready_task_denies_transition_without_event(self):
        self.harness()
        self.db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha)"
            " VALUES(?,?,?,'READY',?)",
            ("f139-nci04-v19-pending", "Wingless", V18, "e" * 64))
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaises(Exception):
                self.transition(allow_v19=True)
        self.assertEqual(self.db.meta(), self.before)
        self.assertEqual(self.v19_events(), [])

    def test_real_verifier_and_cli_do_not_silently_enable_source_promotion(self):
        import f139.local_controller as source
        verify = inspect.getsource(source.Database.verify)
        transition = inspect.getsource(source.Database.transition_source)
        cli = inspect.getsource(source.cli)
        for token in (
            "is_v19 =", "if is_v19:", "v18_terminal_event_sha256",
            "SOURCE_TRANSITION_V19_ORIGINAL_CUSTODY_DRIFT",
            'not any(t["schema"] == "forge.f139.source-transition.v19"',
        ):
            self.assertIn(token, verify)
        self.assertIn("allow_v19: bool = False", transition)
        self.assertIn('SingleOwner.held(self.filename.with_suffix(".lock"))', transition)
        self.assertIn("SOURCE_TRANSITION_V19_ORIGINAL_CUSTODY_REQUIRED", transition)
        self.assertIn("self.event(\"SOURCE_TRANSITION_ADMITTED\", event)", transition)
        # V19 is intentionally exposed only as a one-time, owner-approved
        # CLI.  The ordinary scheduled tick/loop must never call it.
        self.assertIn('transition-qualified-native-v19', cli)
        self.assertIn('transition_v19.add_argument("--approval",type=Path,required=True)', cli)
        self.assertIn('verify_v19_readonly_preflight(validator_db,approval)', cli)
        self.assertIn('allow_v19=True', cli)
        self.assertNotIn('transition-qualified-native-v19',
                         inspect.getsource(source.run_once))


if __name__ == "__main__":
    unittest.main()
