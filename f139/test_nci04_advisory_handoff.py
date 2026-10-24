"""Focused falsification of advisory -> existing native owner PR handoff.

The test provider is synthetic; passing does not activate live science.
"""
from __future__ import annotations

import hashlib
import json
import unittest

from f139.nci04_advisory_handoff import SCHEMA, history_digest
from f139.nci04_autonomy_feed import prepare_feed
from f139.test_nci04_autonomy_feed import FakeProvider


def make_advisory(p: FakeProvider) -> dict:
    history = [{
        "mechanism_sha256": "1" * 64,
        "source_sha": "2" * 40,
        "evidence_sha256": "3" * 64,
        "classification": "NEGATIVE",
    }]
    return {
        "schema": SCHEMA,
        "lane": "Wingless",
        "controller_source_sha": p.source,
        "head_commit": p.head,
        "target_commit": p.parent,
        "path": p.path,
        "after_sha256": hashlib.sha256(p.after).hexdigest(),
        "candidate_id": "causal-novel-001",
        "decision": {
            "schema": "forge.infogain.advisory.v1",
            "lane": "Wingless",
            "frozen_sha256": "4" * 64,
            "history_sha256": history_digest(history),
            "history_preserved": history,
            "negative_count": 1,
            "invalid_count": 0,
            "indeterminate_count": 0,
            "selected": [{
                "id": "causal-novel-001",
                "generator": "dream_rsi",
                "mechanism_sha256": "5" * 64,
                "source_sha": p.head,
                "expected_information_microbits": 150000,
                "estimated_compute_units": 4,
                "status": "UNTESTED_ESTIMATE_NOT_SCIENTIFIC_ACCEPTANCE",
            }],
            "estimated_only": True,
            "scientific_accepted": False,
            "scientific_first_use_authorized": False,
            "dispatch_authorized": False,
            "policy_promotion_authorized": False,
            "accepted_ref_mutation": False,
        },
    }


def report(p: FakeProvider):
    return prepare_feed(p.get, source_sha=p.source,
                        existing_candidate_identities=set())


class AdvisoryHandoffTests(unittest.TestCase):
    def test_valid_decision_binds_existing_verified_pr_and_never_authorizes(self):
        p = FakeProvider()
        p.pr["body"] = json.dumps(make_advisory(p))
        found = report(p)
        self.assertEqual(len(found["candidates"]), 1)
        self.assertFalse(found["rejected"])
        line = found["candidates"][0]["advisory_handoff"]
        self.assertEqual(line["candidate_id"], "causal-novel-001")
        self.assertTrue(line["advisory_only"])
        self.assertFalse(line["scientific_first_use"])
        self.assertFalse(line["dispatch_authorized"])
        self.assertEqual(line["history_sha256"],
                         make_advisory(p)["decision"]["history_sha256"])
        self.assertEqual(json.loads(found["candidates"][0]["issue_body"])[
            "schema"], "forge.f139.nci04.owner-native-development.v1")

    def test_missing_advisory_preserves_owner_only_behavior(self):
        p = FakeProvider()
        found = report(p)
        self.assertEqual(len(found["candidates"]), 1)
        self.assertIsNone(found["candidates"][0]["advisory_handoff"])

    def test_normal_pr_description_without_schema_is_inert(self):
        p = FakeProvider()
        p.pr["body"] = "Source-qualified engineering development; no advisory."
        self.assertEqual(len(report(p)["candidates"]), 1)

    def deny(self, alter, expected="ADVISORY_HANDOFF_INVALID"):
        p = FakeProvider()
        advisory = make_advisory(p)
        alter(advisory)
        p.pr["body"] = json.dumps(advisory)
        result = report(p)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(len(result["rejected"]), 1)
        self.assertIn(expected, result["rejected"][0]["reason"])

    def test_wrong_native_after_hash_denied(self):
        self.deny(lambda a: a.update(after_sha256="f" * 64))

    def test_mismatched_original_controller_source_denied(self):
        self.deny(lambda a: a.update(controller_source_sha="f" * 40))

    def test_advisory_cannot_claim_dispatch_authorization(self):
        self.deny(lambda a: a["decision"].update(dispatch_authorized=True))

    def test_advisory_cannot_claim_scientific_acceptance(self):
        self.deny(lambda a: a["decision"].update(scientific_accepted=True))

    def test_advisory_requires_unique_selected_candidate(self):
        self.deny(lambda a: a["decision"]["selected"].append(
            dict(a["decision"]["selected"][0])))

    def test_consumed_historical_mechanism_denied(self):
        self.deny(lambda a: a["decision"]["selected"][0].update(
            mechanism_sha256="1" * 64))

    def test_history_cannot_be_rewritten_without_pin(self):
        self.deny(lambda a: a["decision"]["history_preserved"][0].update(
            classification="SUPPORTED"))

    def test_wrong_lane_denied(self):
        self.deny(lambda a: a.update(lane="Yggdrasil"))

    def test_zero_information_denied(self):
        self.deny(lambda a: a["decision"]["selected"][0].update(
            expected_information_microbits=0))

    def test_generator_must_be_supported(self):
        self.deny(lambda a: a["decision"]["selected"][0].update(
            generator="paid-api-model"))

    def test_non_owner_remains_rejected_even_with_valid_advisory(self):
        p = FakeProvider()
        p.pr["body"] = json.dumps(make_advisory(p))
        p.pr["user"] = {"login": "attacker"}
        found = report(p)
        self.assertFalse(found["candidates"])
        self.assertIn("PR_NOT_EXPLICIT_OWNER_CANDIDATE",
                      found["rejected"][0]["reason"])

    def test_different_advisory_changes_only_evidence_identity(self):
        p = FakeProvider()
        before = report(p)["candidates"][0]
        p.pr["body"] = json.dumps(make_advisory(p))
        after = report(p)["candidates"][0]
        self.assertEqual(before["issue_body"], after["issue_body"])
        self.assertEqual(before["candidate_identity"], after["candidate_identity"])
        self.assertNotEqual(before["source_evidence_sha256"],
                            after["source_evidence_sha256"])


if __name__ == "__main__":
    unittest.main()
