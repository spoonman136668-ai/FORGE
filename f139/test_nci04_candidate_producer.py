"""Source-only tests for actual structural generation and confounding caveats."""
from __future__ import annotations

import hashlib
import unittest

from f139.nci04_candidate_producer import (
    CandidateProducerDenied, candidate_mechanism_identity, produce,
)

PARENT = "9" * 40
HISTORY = "e" * 64
SOURCE = b'''class PublicCausalCells:
    ACTIVE_SLOTS = 7
    RETAINED_SLOTS = 9

    def __init__(self):
        self._counts = [[[0, 0] for _ in range(2)] for _ in range(16)]

    def choose(self, address: int, *, retained: bool = False) -> int | None:
        cell = address + (self.ACTIVE_SLOTS if retained else 0)
        (zero0, one0), (zero1, one1) = self._counts[cell]
        trials0 = zero0 + one0
        trials1 = zero1 + one1
        if not trials0 or not trials1:
            return None
        lhs, rhs = one0 * trials1, one1 * trials0
        if lhs == rhs:
            return None
        return 0 if lhs > rhs else 1
'''


def build(source=SOURCE, **overrides):
    values = {
        "lane": "Yggdrasil",
        "path": "yggdrasil/public_causal_cells.py",
        "parent_commit": PARENT,
        "before_bytes": source,
        "pinned_before_sha256": hashlib.sha256(source).hexdigest(),
        "history_sha256": HISTORY,
        "consumed_mechanism_sha256": set(),
    }
    values.update(overrides)
    return produce(**values)


def generated_class(source=SOURCE):
    candidate = build(source)
    namespace = {}
    exec(compile(candidate["source"], "<fixed-fixture>", "exec"), namespace)
    return namespace["PublicCausalCells"]


class CandidateProducerTests(unittest.TestCase):
    def test_distinct_pinned_source_created_deterministically(self):
        a, b = build(), build()
        self.assertEqual(a, b)
        self.assertNotEqual(a["source"], SOURCE)
        self.assertEqual(a["record"]["parent_commit"], PARENT)
        self.assertEqual(a["record"]["history_sha256"], HISTORY)
        self.assertEqual(
            hashlib.sha256(a["source"]).hexdigest(),
            a["record"]["after_sha256"])
        self.assertRegex(a["candidate_identity"], r"^[a-f0-9]{64}$")
        self.assertTrue(a["pr_title"].startswith("F139 autonomy DEV:"))
        self.assertFalse(a["record"]["scientific_first_use"])
        self.assertFalse(a["record"]["dispatch_authorized"])
        self.assertFalse(a["record"]["independent_scientific_acceptance"])

    def test_learns_public_outcomes_and_uses_cross_context_only_when_sparse(self):
        cls = generated_class()
        model = cls()
        self.assertIsNone(model.choose(0))
        for _ in range(7):
            model._counts[1][0][1] += 1
            model._counts[1][1][0] += 1
        self.assertEqual(model.choose(0), 0)
        # Retained tier is forbidden as a source for active-tier pooling.
        for _ in range(40):
            model._counts[8][0][0] += 1
            model._counts[8][1][1] += 1
        self.assertEqual(model.choose(0), 0)

    def test_active_never_reads_retained_tier(self):
        cls = generated_class()
        model = cls()
        model._counts[7][0][1] = 10
        model._counts[7][1][0] = 10
        self.assertIsNone(model.choose(0))
        # Within retained tier, unseen address 1 *can* pool evidence from 0.
        self.assertEqual(model.choose(1, retained=True), 0)

    def test_local_arms_take_precedence_even_if_other_context_disagrees(self):
        cls = generated_class()
        model = cls()
        model._counts[0][0][1] = 5
        model._counts[0][1][0] = 5
        model._counts[1][0][0] = 100
        model._counts[1][1][1] = 100
        self.assertEqual(model.choose(0), 0)

    def test_no_leakage_when_both_arms_unobserved_across_pool(self):
        cls = generated_class()
        self.assertIsNone(cls().choose(0))

    def test_confounded_pooling_is_falsifiable_not_scientific_positive(self):
        cls = generated_class()
        model = cls()
        model._counts[1][0][1] = 9
        model._counts[1][1][0] = 9
        self.assertEqual(model.choose(0), 0)
        # A withheld counterfactual at context 0 may be the opposite.
        # This fixture therefore documents a real negative-risk mechanism,
        # not an assertion of generalization or scientific acceptance.
        self.assertFalse(build()["record"]["independent_scientific_acceptance"])

    def test_consumed_mechanism_denied(self):
        with self.assertRaisesRegex(CandidateProducerDenied, "ALREADY_CONSUMED"):
            build(consumed_mechanism_sha256={candidate_mechanism_identity()})

    def test_source_byte_or_parent_identity_drift_denied(self):
        with self.assertRaisesRegex(CandidateProducerDenied, "INPUT_OR_AUTHORITY_DRIFT"):
            build(pinned_before_sha256="f" * 64)
        with self.assertRaisesRegex(CandidateProducerDenied, "INPUT_OR_AUTHORITY_DRIFT"):
            build(parent_commit="not-a-commit")

    def test_no_new_science_authority_or_other_lane(self):
        with self.assertRaisesRegex(CandidateProducerDenied, "INPUT_OR_AUTHORITY_DRIFT"):
            build(scientific_first_use=True)
        with self.assertRaisesRegex(CandidateProducerDenied, "INPUT_OR_AUTHORITY_DRIFT"):
            build(lane="Wingless")

    def test_source_boundary_missing_or_duplicated_denied(self):
        with self.assertRaisesRegex(CandidateProducerDenied, "NATIVE_CONTEXT_NOT_FROZEN"):
            build(SOURCE.replace(b"        if not trials0 or not trials1:\n", b"        if trials0 == 0 or not trials1:\n"))
        with self.assertRaisesRegex(CandidateProducerDenied, "NATIVE_CONTEXT_NOT_FROZEN"):
            build(SOURCE + b"\n" + SOURCE)

    def test_caller_cannot_smuggle_arbitrary_replacement_or_extra_fields(self):
        with self.assertRaises(TypeError):
            build(replacement="import os")
        with self.assertRaisesRegex(CandidateProducerDenied, "INPUT_OR_AUTHORITY_DRIFT"):
            build(consumed_mechanism_sha256={"not-sha"})


if __name__ == "__main__":
    unittest.main()
