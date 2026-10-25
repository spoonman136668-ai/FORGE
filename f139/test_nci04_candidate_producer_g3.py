"""G3 bounded native source proposal: independently falsifiable source tests."""
from __future__ import annotations

import hashlib
import unittest

from f139.nci04_candidate_producer_g3 import (
    G3Denied, MECHANISM, mechanism_identity, produce_g3,
)
from f139.test_nci04_candidate_producer import SOURCE

PARENT = "9" * 40
HISTORY = "e" * 64


def build(source=SOURCE, **overrides):
    args = dict(lane="Yggdrasil", path="yggdrasil/public_causal_cells.py",
                parent_commit=PARENT, original=source,
                original_sha256=hashlib.sha256(source).hexdigest(),
                history_sha256=HISTORY, consumed_mechanisms=set(),
                consumed_candidates=set())
    args.update(overrides)
    return produce_g3(**args)


class G3Tests(unittest.TestCase):
    def test_deterministic_identity_and_distinct_mechanism(self):
        first, second = build(), build()
        self.assertEqual(first, second)
        self.assertNotEqual(first["source"], SOURCE)
        self.assertEqual(first["record"]["mechanism"], MECHANISM)
        self.assertEqual(first["record"]["mechanism_sha256"], mechanism_identity())
        self.assertFalse(first["record"]["dispatch_authorized"])
        self.assertFalse(first["record"]["scientific_first_use"])
        self.assertEqual(first["record"]["independent_unfamiliar_transfer"], "NOT_TESTED")

    def test_sparse_local_abstention_then_decision(self):
        namespace = {}
        exec(compile(build()["source"], "<frozen-test-fixture>", "exec"), namespace)
        cell = namespace["PublicCausalCells"]()
        for _ in range(2):
            cell._counts[0][0][1] += 1
            cell._counts[0][1][0] += 1
        self.assertIsNone(cell.choose(0))
        cell._counts[0][0][1] += 1
        cell._counts[0][1][0] += 1
        self.assertEqual(cell.choose(0), 0)

    def test_other_address_evidence_not_borrowed(self):
        namespace = {}
        exec(compile(build()["source"], "<frozen-test-fixture>", "exec"), namespace)
        cell = namespace["PublicCausalCells"]()
        for _ in range(30):
            cell._counts[1][0][1] += 1
            cell._counts[1][1][0] += 1
        self.assertIsNone(cell.choose(0))

    def test_negative_risk_is_explicit_not_promoted(self):
        self.assertIn("slower_learning", build()["record"]["negative_risks"])
        self.assertFalse(build()["record"]["publish_authorized"])

    def test_consumed_mechanism_or_candidate_rejected(self):
        item = build()
        with self.assertRaisesRegex(G3Denied, "MECHANISM_CONSUMED"):
            build(consumed_mechanisms={mechanism_identity()})
        with self.assertRaisesRegex(G3Denied, "CANDIDATE_CONSUMED"):
            build(consumed_candidates={item["candidate_identity"]})

    def test_source_drift_invalid_or_duplicate_anchor_fails(self):
        with self.assertRaisesRegex(G3Denied, "SOURCE_ANCHOR_DRIFT"):
            build(SOURCE.replace(b"        if not trials0 or not trials1:\n",
                                 b"        if trials0 <= 0 or trials1 <= 0:\n"))
        with self.assertRaisesRegex(G3Denied, "SOURCE_ANCHOR_DRIFT"):
            build(SOURCE + SOURCE)

    def test_no_science_or_other_lane(self):
        with self.assertRaisesRegex(G3Denied, "INPUT_OR_CUSTODY_INVALID"):
            build(scientific_first_use=True)
        with self.assertRaisesRegex(G3Denied, "INPUT_OR_CUSTODY_INVALID"):
            build(lane="Wingless")
        with self.assertRaisesRegex(G3Denied, "INPUT_OR_CUSTODY_INVALID"):
            build(original_sha256="0" * 64)


if __name__ == "__main__":
    unittest.main()
