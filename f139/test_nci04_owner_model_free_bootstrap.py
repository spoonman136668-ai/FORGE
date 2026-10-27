"""No-network original owner model-free bootstrap integration qualification."""
from __future__ import annotations

import inspect
import json
import unittest
from unittest.mock import patch

from f139 import nci04_candidate_producer_g29 as g29
from f139 import nci04_research_steering as steering
from f139.local_controller import run_once
from f139.nci04_model_owner_publication import ATTEMPT, SUCCESS
from f139.nci04_owner_model_free_bootstrap import (
    LocalBootstrapDenied, local_proposal_once, original_canonical_db)
from f139.nci04_owner_ledger import activate_native, admit_native_issue
from f139.test_nci04_candidate_publisher import FakeOriginalOwner
from f139.test_nci04_candidate_producer_g29 import BEFORE
from f139.test_nci04_research_steering import SteeringProvider
from test_nci04_owner_ledger import LedgerTests, MAIN


class LocalG29OriginalOwnerTests(unittest.TestCase):
    def setUp(self):
        f = LedgerTests("test_admit_exactly_once_and_verify_original_ledger")
        f.setUp()
        self.addCleanup(f.doCleanups)
        self.fixture = f
        self.db = f.db
        self.assertTrue(activate_native(self.db, f.approval()))
        # G29's authentic structural requirement includes a class-local
        # _address method missing from G1's deliberately smaller fixture.
        # Keep the fake's before SHA and commit assertions aligned exactly.
        source_patch = patch("f139.test_nci04_candidate_publisher.SOURCE", BEFORE)
        source_patch.start()
        self.addCleanup(source_patch.stop)
        self.owner = FakeOriginalOwner()
        self.owner.source = MAIN
        self.steering = SteeringProvider()
        for change in (
            patch.object(steering, "DOCUMENTS", self.steering.documents),
            patch.object(g29, "PARENT", self.owner.parent),
        ):
            change.start()
            self.addCleanup(change.stop)

    def publish(self, witness=lambda: True):
        return local_proposal_once(
            self.db, self.owner.get, self.steering.get, self.owner.write,
            source_sha=MAIN, owner_witness=witness)

    def events(self, kind):
        return [json.loads(row["payload"]) for row in self.db.conn.execute(
            "SELECT payload FROM events WHERE kind=? ORDER BY seq", (kind,))]

    def test_one_authentic_source_only_g29_draft_under_original_owner(self):
        old = self.db.meta()["head_seq"]
        got = self.publish()
        self.assertEqual(got["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(got["generator"], "BOUNDED_MODEL_FREE_G29")
        self.assertEqual(got["paid_model_calls"], 0)
        self.assertFalse(got["scientific_first_use"])
        self.assertEqual(self.db.meta()["head_seq"], old + 2)
        self.assertEqual(len(self.events(ATTEMPT)), 1)
        self.assertEqual(len(self.events(SUCCESS)), 1)
        self.assertEqual([m for m, route in self.owner.write_calls],
                         ["POST", "PUT", "POST"])
        self.assertIn("    def probe_uncertain(", self.owner.head_data.decode())
        self.assertNotEqual(self.owner.head_data, BEFORE)
        self.assertEqual(self.owner.pr["draft"], True)
        note = json.loads(self.owner.pr["body"])
        self.assertFalse(note["scientific_first_use"])
        self.assertFalse(note["dispatch_authorized"])
        self.assertEqual(note["schema"], "forge.f139.owner-model-draft-note.v1")
        self.db.verify()

    def test_actual_existing_native_feeder_accepts_generated_owner_draft(self):
        from f139.nci04_autonomy_feed import prepare_feed
        self.assertEqual(self.publish()["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        def get(route):
            if route == ("repos/spoonman136668-ai/Wingless/"
                         "pulls?state=open&per_page=100&page=1"):
                return []
            return self.owner.get(route)
        result = prepare_feed(get, source_sha=MAIN,
                              existing_candidate_identities=set())
        self.assertTrue(result["enabled"])
        self.assertEqual(result["rejected"], [])
        self.assertEqual(len(result["candidates"]), 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["lane"], "Yggdrasil")
        self.assertIn("intent_base64", json.loads(candidate["issue_body"]))
        self.assertFalse(candidate["scientific_first_use"])

    def test_once_only_sticky_original_attempt_does_not_repeat(self):
        self.assertEqual(self.publish()["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        head = self.db.meta()["head_hash"]
        result = self.publish()
        self.assertEqual(result["disposition"],
                         "LOCAL_G29_ALREADY_ATTEMPTED_NO_REPLAY")
        self.assertEqual(self.db.meta()["head_hash"], head)
        self.assertEqual(len(self.owner.write_calls), 3)

    def test_network_partial_write_stays_custodied_and_never_retried(self):
        self.owner.fail_after_reference = True
        got = self.publish()
        self.assertEqual(got["disposition"],
                         "MODEL_DRAFT_REMOTE_AMBIGUOUS_NO_RETRY")
        self.assertEqual(len(self.events(ATTEMPT)), 1)
        self.assertEqual(len(self.events(SUCCESS)), 0)
        self.owner.fail_after_reference = False
        self.assertEqual(self.publish()["disposition"],
                         "LOCAL_G29_ALREADY_ATTEMPTED_NO_REPLAY")
        self.assertEqual(len(self.owner.write_calls), 2)
        self.db.verify()

    def test_original_owner_witness_and_source_pin_fail_before_git_write(self):
        with self.assertRaisesRegex(LocalBootstrapDenied, "ORIGINAL_OWNER"):
            self.publish(witness=lambda: False)
        self.owner.source = "f" * 40
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse(self.owner.write_calls)
        self.assertFalse(self.events(ATTEMPT))

    def test_negative_custody_stays_in_retained_history(self):
        self.assertTrue(admit_native_issue(
            self.db, self.fixture.native, "2026-10-27T09:00:00Z"))
        t = self.fixture.native.ticket
        self.db.claim(t, "2026-10-27T09:01:00Z")
        self.db.quarantine(t, "EXP_UNSUCCESSFUL")
        got = self.publish()
        self.assertEqual(got["disposition"], "MODEL_DRAFT_AUTHENTICATED")
        self.assertEqual(
            self.db.conn.execute(
                "SELECT stage FROM tasks WHERE ticket=?", (t,)
            ).fetchone()["stage"], "QUARANTINED")
        self.db.verify()

    def test_reject_wrong_canonical_database_path(self):
        with self.assertRaisesRegex(LocalBootstrapDenied, "ORIGINAL_DATABASE"):
            original_canonical_db(self.db, self.db.filename.parent / "not-original.sqlite")
        same, close = original_canonical_db(self.db, self.db.filename)
        self.assertIs(same, self.db)
        self.assertFalse(close)

    def test_same_original_runtime_only_no_new_controller_or_subscription_loop(self):
        original_loop = inspect.getsource(run_once)
        self.assertIn("prior_g3", original_loop)
        self.assertIn("run_original_g29_once(", original_loop)
        self.assertIn("native_original_running_publisher_profile(db_path)",
                      original_loop)
        self.assertIn('type(api) is GitHub', original_loop)
        self.assertNotIn("codex exec", original_loop)
        self.assertNotIn("qwen", original_loop)


if __name__ == "__main__":
    unittest.main()
