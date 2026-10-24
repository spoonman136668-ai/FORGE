"""Focused, mock-only G3-to-existing-G2 publisher contract tests.

The fake owner may NEVER be confused with live original-owner custody.
These tests do not publish any real Git ref or initiate F139 execution.
"""
from __future__ import annotations

import unittest

from f139.nci04_candidate_producer import candidate_mechanism_identity
from f139.nci04_candidate_producer_g3 import mechanism_identity
from f139.nci04_candidate_publisher import (
    PublisherDenied, RECIPE_G3, publish_single_draft, publisher_preflight,
)
from f139.test_nci04_candidate_publisher import FakeOriginalOwner


def preflight(owner, *, mechanisms=None, candidates=None):
    return publisher_preflight(
        owner.get, source_sha=owner.source, parent_commit=owner.parent,
        historical_sha256=owner.history,
        consumed_mechanisms=(
            {candidate_mechanism_identity()} if mechanisms is None else mechanisms
        ),
        existing_candidate_identities=set() if candidates is None else candidates,
        recipe=RECIPE_G3,
    )


def publish(owner, plan, *, mechanisms=None, candidates=None, witness=True):
    return publish_single_draft(
        owner.get, owner.write, plan,
        owner_witness=lambda: witness,
        consumed_mechanisms=(
            {candidate_mechanism_identity()} if mechanisms is None else mechanisms
        ),
        existing_candidate_identities=set() if candidates is None else candidates,
    )


class G3PublisherTests(unittest.TestCase):
    def test_g3_preflight_distinct_from_g1_and_never_authorizes_writes(self):
        owner = FakeOriginalOwner()
        plan = preflight(owner)
        self.assertEqual(plan["recipe"], RECIPE_G3)
        self.assertIn(b"if trials0 < 3 or trials1 < 3:", plan["candidate_source"])
        self.assertNotIn(b"pooled0", plan["candidate_source"])
        self.assertFalse(plan["writes_authorized"])
        self.assertEqual(plan["mechanism_sha256"], mechanism_identity())
        self.assertEqual(plan["pr_title"],
                         "F139 autonomy DEV: local evidence confidence gating")

    def test_g3_single_mock_draft_uses_original_feeder(self):
        owner = FakeOriginalOwner()
        plan = preflight(owner)
        result = publish(owner, plan)
        self.assertTrue(result["authentic_single_commit_owner_draft"])
        self.assertTrue(result["source_qualified_for_existing_feeder"])
        self.assertFalse(result["worker_dispatched"])
        self.assertFalse(result["controller_mutated"])
        self.assertEqual([m for m, _ in owner.write_calls],
                         ["POST", "PUT", "POST"])
        self.assertIn("three genuine local observations", owner.pr["body"])
        self.assertNotIn("tier-local pooling", owner.pr["body"])

    def test_g1_negative_must_be_retained_before_any_write(self):
        owner = FakeOriginalOwner()
        with self.assertRaisesRegex(PublisherDenied, "G1_NEGATIVE_HISTORY"):
            preflight(owner, mechanisms=set())
        self.assertEqual(owner.write_calls, [])

    def test_reject_already_consumed_g3_mechanism(self):
        owner = FakeOriginalOwner()
        with self.assertRaisesRegex(PublisherDenied, "PREVIOUSLY_CONSUMED"):
            preflight(owner, mechanisms={
                candidate_mechanism_identity(), mechanism_identity()
            })
        self.assertEqual(owner.write_calls, [])

    def test_reject_candidate_consumed_before_preflight(self):
        owner = FakeOriginalOwner()
        first = preflight(owner)
        with self.assertRaisesRegex(ValueError, "CANDIDATE_CONSUMED"):
            preflight(owner, candidates={first["candidate_identity"]})
        self.assertEqual(owner.write_calls, [])

    def test_owner_revalidates_history_at_publish_time(self):
        owner = FakeOriginalOwner()
        plan = preflight(owner)
        with self.assertRaisesRegex(PublisherDenied, "G1_NEGATIVE_HISTORY"):
            publish(owner, plan, mechanisms=set())
        self.assertEqual(owner.write_calls, [])

    def test_reject_changed_recipe_plan_before_write(self):
        owner = FakeOriginalOwner()
        plan = preflight(owner)
        plan["recipe"] = "g1-tier-local-pooling"
        with self.assertRaisesRegex(PublisherDenied, "PREVIOUSLY_CONSUMED"):
            publish(owner, plan)
        self.assertEqual(owner.write_calls, [])

    def test_original_owner_witness_still_required(self):
        owner = FakeOriginalOwner()
        plan = preflight(owner)
        with self.assertRaisesRegex(PublisherDenied, "OWNER_WRITER_NOT_QUALIFIED"):
            publish(owner, plan, witness=False)
        self.assertEqual(owner.write_calls, [])

    def test_fail_closed_on_moved_history_or_partial_git_write(self):
        owner = FakeOriginalOwner()
        plan = preflight(owner)
        with self.assertRaisesRegex(ValueError, "CANDIDATE_CONSUMED"):
            publish(owner, plan, candidates={plan["candidate_identity"]})
        self.assertEqual(owner.write_calls, [])
        owner.fail_after_reference = True
        with self.assertRaises(ConnectionError):
            publish(owner, plan)
        self.assertEqual(len(owner.write_calls), 2)
        with self.assertRaisesRegex(PublisherDenied, "SOURCE_BRANCH_EXISTS"):
            preflight(owner)

    def test_g1_default_contract_remains_unchanged(self):
        owner = FakeOriginalOwner()
        plan = owner.preflight()
        self.assertEqual(plan["recipe"], "g1-tier-local-pooling")
        self.assertIn(b"pooled0", plan["candidate_source"])


if __name__ == "__main__":
    unittest.main()
