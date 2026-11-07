"""Isolation and falsification tests for the inactive R3 self-source rehearsal."""
from dataclasses import replace
import unittest

from f139.rsi_r3_source_cycle import (
    R3Denied, SCHEMA, fingerprint, generate, rehearsal, source_for, verify,
)

# Deterministic development fixtures. These are NOT new heldout experiments.
G1 = ((1, (20, 5, 3, 1)), (2, (17, 1, 8, 1)), (3, (15, 2, 2, 9)))
G2 = ((2, (18, 4, 1, 1)), (3, (16, 1, 4, 9)))


class SelfSourceTests(unittest.TestCase):
    def test_g1_source_is_executed_to_create_distinct_g2_source(self):
        a, b = rehearsal(G1, G2)
        self.assertEqual((a.generation, b.generation), (1, 2))
        self.assertEqual((a.operator, b.operator), (1, 3))
        self.assertEqual(b.parent_sha256, a.source_sha256)
        self.assertNotEqual(a.parent_source, a.source)
        self.assertNotEqual(b.parent_source, b.source)
        self.assertTrue(verify((a, b)))
        # If G0, rather than generated G1, secretly selected G2, the next
        # operator would be 2, not 3. A parent replay is thus distinguishable.
        baseline = generate(parent_source=source_for(0), generation=2,
                            feedback=G2, used_operators=frozenset({0, 1}))
        self.assertEqual(baseline.operator, 2)
        self.assertNotEqual(baseline.source_sha256, b.source_sha256)
        self.assertIn(b"def rank(row):", b.source)
        compile(b.source, "<actual-g2-source>", "exec")

    def test_parent_source_or_observation_tamper_fails_closed(self):
        a, b = rehearsal(G1, G2)
        changes = [
            replace(b, parent_sha256="0" * 64),
            replace(b, parent_source=a.parent_source),
            replace(b, source_sha256="0" * 64),
            replace(b, feedback_sha256="0" * 64),
            replace(b, observed_training=((2, (50, 4, 1, 1)), G2[1])),
            replace(b, operator=2),
            replace(b, generation=1),
            replace(b, schema="unknown"),
        ]
        for tampered in changes:
            with self.subTest(tampered=tampered):
                with self.assertRaises(R3Denied):
                    verify((a, tampered))

    def test_source_grammar_and_budget_reject_arbitrary_execution(self):
        with self.assertRaisesRegex(R3Denied, "UNREGISTERED_OR_TAMPERED_SOURCE"):
            generate(parent_source=b"import os\nos.system('bad')",
                     generation=1, feedback=G1,
                     used_operators=frozenset({0}))
        with self.assertRaises(R3Denied):
            generate(parent_source=source_for(0), generation=3, feedback=G1,
                     used_operators=frozenset({0}))
        for wrong in (None, "0", 4, -1, True):
            with self.subTest(wrong=wrong), self.assertRaises(R3Denied):
                source_for(wrong)

    def test_negative_feedbacks_do_not_select_unsafe_candidates(self):
        rejected = [
            ((1, (-1, 0, 0, 0)),),
            ((1, (1, 0, 0, 0)), (1, (2, 0, 0, 0))),
            ((7, (1, 0, 0, 0)),),
            ((1, (True, 0, 0, 0)),),
            ((1, (1, 0, 0)),),
            ((0, (1, 0, 0, 0)),),
            ((1, (float('nan'), 0, 0, 0)),),
        ]
        for rows in rejected:
            with self.subTest(rows=rows), self.assertRaises(R3Denied):
                generate(parent_source=source_for(0), generation=1,
                         feedback=rows, used_operators=frozenset({0}))

    def test_identical_rehearsal_preserves_hashes_and_source_custody(self):
        left, right = rehearsal(G1, G2), rehearsal(G1, G2)
        self.assertEqual(left, right)
        self.assertEqual(left[0].source_sha256, fingerprint(left[0].source))
        self.assertEqual(left[1].parent_sha256, left[0].source_sha256)
        self.assertEqual(left[1].schema, SCHEMA)
        self.assertNotIn(b"subprocess", left[1].source)
        self.assertNotIn(b"open(", left[1].source)


if __name__ == "__main__":
    unittest.main()
