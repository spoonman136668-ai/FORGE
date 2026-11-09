"""R12-C historical anchor and original-owner issuance negative controls.

Synthetic source/ledger events are NOT real original-owner authority.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from f139.local_controller import Database, canonical
from f139.rsi_r11_owner_once import KIND as RESERVATION_KIND
from f139.rsi_r12_candidate_binding import (
    binding_from_reservation_event,
)
from f139.rsi_r12b_signed_job import (
    _development_signature, prepare,
)
from f139.rsi_r12c_original_spend import (
    KIND, OriginalIssueDenied, audit_issuance, event_payload,
    validate_event, issue_original_once,
)
from f139.test_rsi_r12b_signed_job import KEY, MAIN, TREE
from f139.test_rsi_r12_candidate_binding import fixture

SOURCE = "c" * 40


def fixture_event():
    reservation, candidate = fixture()
    origin = {
        "seq": 24, "sha": "a" * 64,
        "prior_sha": reservation["prior_event_head_sha256"],
        "payload": canonical(reservation).decode("ascii"),
    }
    binding = binding_from_reservation_event(
        reservation=reservation, row=origin,
        expected_owner_source_sha=SOURCE)
    intent = prepare(
        binding=binding, source_sha=MAIN,
        source_tree_sha=TREE, worker_run_id=42570000000,
        worker_job_id=128999999999, runner_os="windows-latest")
    sig = _development_signature(KEY, intent)
    event = {"seq": 32, "prior_sha": "f" * 64}
    doc = event_payload(
        binding=binding, intent=intent,
        signature=sig, prior_head=event["prior_sha"])
    return doc, event, binding, candidate


class OriginalIssueTests(unittest.TestCase):
    def test_canonical_issuance_contract_remains_inert(self):
        doc, row, binding, _ = fixture_event()
        validate_event(
            payload=doc, event_row=row, binding=binding,
            source_at_event=SOURCE)
        self.assertEqual(
            binding["original_owner_ledger_head_sha256"],
            binding["reservation_event_sha256"])
        self.assertEqual(doc["one_job_maximum"], 1)
        self.assertFalse(doc["worker_admitted"])
        self.assertFalse(doc["worker_dispatched"])
        self.assertFalse(doc["credential_free_worker_admitted"])

    def test_rejects_history_tamper_replay_and_false_worker_authority(self):
        doc, row, binding, _ = fixture_event()
        for key, value in (
            ("reservation_seq", 25),
            ("reservation_event_sha256", "b" * 64),
            ("original_owner_ledger_head_sha256", "b" * 64),
            ("binding_sha256", "b" * 64),
            ("intent_sha256", "b" * 64),
            ("signature_sha256", "not-a-sha"),
            ("prior_event_head_sha256", "e" * 64),
            ("one_job_maximum", 2),
            ("retry_allowed", True),
            ("development_only", False),
            ("worker_admitted", True),
            ("worker_dispatched", True),
            ("credential_free_worker_admitted", True),
            ("paid_model_calls", 1),
            ("scientific_first_use", True),
            ("source_promoted", True),
            ("autonomous_rsi_proven", True),
        ):
            with self.subTest(field=key):
                bad = dict(doc)
                bad[key] = value
                with self.assertRaises(OriginalIssueDenied):
                    validate_event(
                        payload=bad, event_row=row, binding=binding,
                        source_at_event=SOURCE)
        bad = dict(doc)
        bad["intent"] = {**doc["intent"], "worker_run_attempt": 2}
        with self.assertRaises(OriginalIssueDenied):
            validate_event(
                payload=bad, event_row=row, binding=binding,
                source_at_event=SOURCE)
        with self.assertRaises(OriginalIssueDenied):
            validate_event(
                payload=doc, event_row=row, binding=binding,
                source_at_event="b" * 40)
        with self.assertRaises(OriginalIssueDenied):
            validate_event(
                payload=doc, event_row={"seq": 24,
                                        "prior_sha": row["prior_sha"]},
                binding=binding, source_at_event=SOURCE)

    def test_original_issuance_denies_disabled_or_synthetic_ledger(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        db = Database.initialize(Path(temp.name) / "state.sqlite", SOURCE)
        self.addCleanup(db.close)
        head = db.meta()["head_hash"]
        self.assertEqual(audit_issuance(db), ())
        doc, row, binding, candidate = fixture_event()
        with self.assertRaises(Exception):
            issue_original_once(
                db=db, provider=object(), candidate=candidate,
                signing_key=KEY, protected_main_sha=MAIN,
                protected_main_tree_sha=TREE,
                worker_run_id=42570000000,
                worker_job_id=128999999999, runner_os="windows-latest")
        self.assertEqual(db.meta()["head_hash"], head)
        db.event(KIND, doc)
        with self.assertRaises(OriginalIssueDenied):
            audit_issuance(db)
        with self.assertRaises(Exception):
            db.verify()

    def test_owner_policy_explicitly_excludes_forge_self(self):
        from f139.rsi_r12c_original_spend import (
            owner_self_policy_allows,
        )
        # Matches the ORIGINAL operator policy issue #807 as currently
        # published, with no FORGE-self allowance. Only an authenticated
        # operator policy amendment can open the future original issuance.
        policy = {
            "schema": "forge.f139.native-autonomy-feed-owner-policy.v1",
            "enabled": True, "source_sha": SOURCE,
            "lanes": ["Wingless", "Yggdrasil"],
            "max_issue_creations_per_cycle": 2,
            "new_controller": False, "new_scheduler": False,
            "new_queue": False, "scientific_first_use": False,
            "paid_model_calls": 0, "accepted_ref_mutations": 0,
        }
        self.assertFalse(owner_self_policy_allows(
            policy, original_source_sha=SOURCE))
        positive = {**policy, "lanes": [
            "Wingless", "Yggdrasil", "FORGE-self"]}
        # Only a synthetic shape check, not a signed operator policy.
        self.assertTrue(owner_self_policy_allows(
            positive, original_source_sha=SOURCE))
        for key, value in (
            ("source_sha", "f" * 40),
            ("enabled", False),
            ("scientific_first_use", True),
            ("paid_model_calls", 1),
            ("new_scheduler", True),
            ("new_queue", True),
            ("accepted_ref_mutations", 1),
            ("max_issue_creations_per_cycle", 9),
            ("lanes", ["Wingless", "FORGE-self", "FORGE-self"]),
        ):
            with self.subTest(key=key):
                altered = {**positive, key: value}
                self.assertFalse(owner_self_policy_allows(
                    altered, original_source_sha=SOURCE))

    def test_original_workflow_and_owner_lanes_remain_unchanged(self):
        from f139.verify_ticket import LANES as WORKER
        from f139.local_controller import LANES as OWNER
        self.assertNotIn("FORGE-self", WORKER)
        self.assertNotIn("FORGE-self", OWNER)


if __name__ == "__main__":
    unittest.main()
