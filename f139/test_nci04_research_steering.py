"""Focused deterministic tests for merged-source ITD-02 steering consumption.

No GitHub network, controller, original-world episodes or scientific first use.
"""
from __future__ import annotations

import base64
import hashlib
import unittest
from unittest.mock import patch

from f139 import nci04_research_steering as steering
from f139.nci04_autonomy_feed import NativeFeedDenied, prepare_feed
from f139.test_nci04_autonomy_feed import FakeProvider


def blob(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


class SteeringProvider:
    """Synthetic fixture with exact Git blob checks and existing PR behavior."""

    def __init__(self):
        self.original = FakeProvider()
        self.raws = {
            steering.DOCUMENTS[0][0]:
                b"# FORGE advisory\nCORE-NATIVE-INTELLIGENCE.md\n"
                b"LEARNING-MECHANISM-DISCOVERY.md\n"
                b"INDEPENDENT-SCIENTIFIC-VALIDATION.md\n",
            steering.DOCUMENTS[1][0]:
                b"Decision-discriminating source-native integration\n",
            steering.DOCUMENTS[2][0]:
                b"Learning-progress and Multi-fidelity prioritization\n",
            steering.DOCUMENTS[3][0]:
                b"independent development ablation confirmation\n",
        }
        self.files = {
            path: (blob(raw), raw) for path, raw in self.raws.items()
        }

    @property
    def documents(self):
        return tuple((path, sha) for path, (sha, _) in self.files.items())

    def get(self, route):
        prefix = "repos/" + steering.REPOSITORY + "/contents/"
        if route.startswith(prefix):
            path, sep, ref = route[len(prefix):].partition("?ref=")
            if not sep or ref != steering.MERGED_STEERING_COMMIT:
                raise AssertionError("unapproved steering ref")
            sha, raw = self.files[path]
            return {
                "type": "file", "encoding": "base64",
                "size": len(raw), "sha": sha,
                "content": base64.b64encode(raw).decode("ascii"),
            }
        return self.original.get(route)


class SteeringIntakeTests(unittest.TestCase):
    def fixture(self):
        fixture = SteeringProvider()
        self.addCleanup(patch.stopall)
        patch.object(steering, "DOCUMENTS", fixture.documents).start()
        return fixture

    def test_four_source_pinned_documents_advisory_only(self):
        p = self.fixture()
        result = steering.read_approved_steering(p.get)
        self.assertEqual(result["status"], "VERIFIED_ADVISORY_ONLY")
        self.assertEqual(result["documents"], 4)
        self.assertEqual(result["source_commit"],
                         steering.MERGED_STEERING_COMMIT)
        self.assertTrue(result["next_eligible_development_only"])
        for key in ("scientific_first_use", "dispatch_authorized",
                    "accepted_ref_mutation"):
            self.assertFalse(result[key])

    def test_existing_native_candidate_identical_with_steering(self):
        p = self.fixture()
        legacy = prepare_feed(
            p.get, source_sha=p.original.source,
            existing_candidate_identities=set())
        guided = prepare_feed(
            p.get, source_sha=p.original.source,
            existing_candidate_identities=set(), steering_get=p.get)
        self.assertEqual(guided["steering"]["status"],
                         "VERIFIED_ADVISORY_ONLY")
        self.assertEqual(guided["candidates"][0]["candidate_identity"],
                         legacy["candidates"][0]["candidate_identity"])
        self.assertEqual(guided["candidates"][0]["issue_body"],
                         legacy["candidates"][0]["issue_body"])
        self.assertEqual(guided["rejected"], [])

    def test_source_bound_steering_selection_is_observable_and_non_authoritative(self):
        p = self.fixture()
        snapshots = [
            prepare_feed(p.get, source_sha=p.original.source,
                         existing_candidate_identities=set(), steering_get=p.get)
            for _ in range(2)
        ]
        evidence = snapshots[0]["steering"]["selection_witness"]
        self.assertEqual(evidence["schema"], "forge.f139.itd02-selection-witness.v1")
        self.assertEqual(evidence["eligible_authenticated_count"], 1)
        self.assertEqual(evidence["selected_authenticated_count"], 1)
        self.assertEqual(evidence["selected_advisory_forecast_count"], 0)
        self.assertFalse(evidence["selection_differs_from_catalog_prefix"])
        self.assertRegex(evidence["source_selection_sha256"], r"^[a-f0-9]{64}$")
        self.assertTrue(evidence["development_only"])
        self.assertFalse(evidence["scientific_first_use"])
        self.assertFalse(evidence["dispatch_authorized"])
        self.assertEqual(evidence, snapshots[1]["steering"]["selection_witness"])
        self.assertEqual(
            [c["candidate_identity"] for c in snapshots[0]["candidates"]],
            [c["candidate_identity"] for c in snapshots[1]["candidates"]])
        self.assertEqual(
            [c["issue_body"] for c in snapshots[0]["candidates"]],
            [c["issue_body"] for c in snapshots[1]["candidates"]])

    def test_disabled_feed_does_not_read_guidance(self):
        p = self.fixture()
        p.original.policy["enabled"] = False
        self.assertEqual(
            prepare_feed(p.get, source_sha=p.original.source,
                         existing_candidate_identities=set(),
                         steering_get=lambda _: 1 / 0),
            {"enabled": False, "candidates": [], "rejected": []})

    def test_wrong_document_blob_fail_closed(self):
        p = self.fixture()
        original = p.get
        def bad(route):
            doc = original(route)
            if "CORE-NATIVE-INTELLIGENCE.md" in route:
                doc = dict(doc, sha="a" * 40)
            return doc
        with self.assertRaisesRegex(
                NativeFeedDenied, "STEERING_SOURCE_UNQUALIFIED"):
            prepare_feed(p.get, source_sha=p.original.source,
                         existing_candidate_identities=set(),
                         steering_get=bad)

    def test_same_sha_but_mutated_bytes_fail_closed(self):
        p = self.fixture()
        original = p.get
        def bad(route):
            doc = original(route)
            if "CORE-NATIVE-INTELLIGENCE.md" in route:
                doc = dict(doc, content=base64.b64encode(
                    b"decision-discriminating fake integration").decode())
            return doc
        with self.assertRaises(steering.SteeringDenied):
            steering.read_approved_steering(bad)

    def test_advisory_provider_outage_keeps_legacy_intake(self):
        p = self.fixture()
        legacy = prepare_feed(p.get, source_sha=p.original.source,
                              existing_candidate_identities=set())
        def offline(route):
            if "/contents/docs/" in route:
                raise RuntimeError("F139_GITHUB_API_TIMEOUT")
            return p.get(route)
        guided = prepare_feed(
            p.get, source_sha=p.original.source,
            existing_candidate_identities=set(), steering_get=offline)
        self.assertEqual(guided["steering"]["status"],
                         "UNAVAILABLE_LEGACY_ORDER")
        self.assertEqual(guided["candidates"], legacy["candidates"])
        self.assertEqual(guided["rejected"], legacy["rejected"])

    def test_source_scope_mismatch_denied(self):
        p = self.fixture()
        path = steering.DOCUMENTS[1][0]
        raw = b"unrelated program, no native integration"
        p.files[path] = (blob(raw), raw)
        with patch.object(steering, "DOCUMENTS", p.documents):
            with self.assertRaisesRegex(
                    steering.SteeringDenied, "DOCUMENT_SCOPE_INVALID"):
                steering.read_approved_steering(p.get)

    def test_forecast_priority_only_within_authenticated_candidates(self):
        eligible = [
            {"lane": "Wingless", "pr_number": 1, "advisory_handoff": None},
            {"lane": "Wingless", "pr_number": 2, "advisory_handoff": {
                "advisory_only": True, "expected_information_microbits": 400,
                "estimated_compute_units": 2}},
            {"lane": "Yggdrasil", "pr_number": 3, "advisory_handoff": None},
        ]
        ranked = steering.rank_eligible(eligible)
        self.assertEqual([x["pr_number"] for x in ranked], [2, 3])
        self.assertEqual(len(ranked), 2)

    def test_without_forecast_legacy_order_per_lane_preserved(self):
        eligible = [
            {"lane": "Wingless", "pr_number": 9},
            {"lane": "Wingless", "pr_number": 10},
            {"lane": "Yggdrasil", "pr_number": 11},
        ]
        self.assertEqual([x["pr_number"] for x in
                          steering.rank_eligible(eligible)], [9, 11])

    def test_no_authority_widening_from_ranker(self):
        with self.assertRaisesRegex(
                steering.SteeringDenied, "RANK_INPUT_INVALID"):
            steering.rank_eligible([
                {"lane": "KTRADE", "scientific_first_use": True}])
        with self.assertRaisesRegex(
                steering.SteeringDenied, "RANK_INPUT_INVALID"):
            steering.rank_eligible([], maximum=999)

    def test_actual_operator_merged_pin_has_four_known_hashes(self):
        # Scope pins ensure this test won't silently bless an unrelated file.
        self.assertEqual(len(steering.DOCUMENTS), 4)
        self.assertEqual(steering.MERGED_STEERING_COMMIT,
                         "2a3c9453ba36c983b7b1dee0bb6ab1371108141b")


if __name__ == "__main__":
    unittest.main()
