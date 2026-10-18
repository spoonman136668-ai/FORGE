"""F124-AR focused deterministic source-only qualification.

No experimental TRAIN selection and no DEV materialization here.
"""
import unittest
from collections import Counter

import f124ar_train_source as source
import f124aq_train_source as parent


class FrozenSourceGate(unittest.TestCase):
    def test_exact_frozen_identity_and_no_dev(self):
        doc = source.frozen()
        self.assertEqual(source.witness.blob(source.FREEZE), source.FREEZE_BLOB)
        self.assertEqual(source.witness.blob(parent.__file__), source.PARENT_BLOB)
        self.assertEqual(
            doc["lineage"]["qualified_parent_head"], source.PARENT_HEAD)
        self.assertEqual(
            doc["qualification"]["authority"]["merge"], False)
        self.assertTrue(set(source.OPERATORS["TRAIN"]).isdisjoint(
            source.OPERATORS["DEV"]))
        for lane in source.COHORTS:
            self.assertTrue(set(source.COHORTS[lane]["TRAIN"]).isdisjoint(
                source.COHORTS[lane]["DEV"]))
            with self.assertRaises(Exception):
                source.pairs(lane, "DEV")
            with self.assertRaises(Exception):
                source.build(lane, source.COHORTS[lane]["DEV"].start,
                             source.VECTORS[0], "TRAIN")
            with self.assertRaises(Exception):
                source.build(lane, source.COHORTS[lane]["DEV"].start,
                             source.VECTORS[0], "DEV")
        with self.assertRaises(Exception):
            source.pairs("unknown", "TRAIN")

    def test_fresh_train_provenance_and_symmetric_noisy_demos(self):
        old_ops = set(parent.OPERATORS["TRAIN"]) | set(parent.OPERATORS["DEV"])
        new_ops = set(source.OPERATORS["TRAIN"]) | set(source.OPERATORS["DEV"])
        self.assertTrue(old_ops.isdisjoint(new_ops))
        for lane in source.COHORTS:
            rows = source.pairs(lane, "TRAIN")
            self.assertEqual(len(rows), 48)
            self.assertEqual(Counter(row[2] for row in rows),
                             Counter({family: 12 for family in source.FAMILIES}))
            for _, vector, family, operator, nonce, p, n in rows:
                self.assertIn(family, source.FAMILIES)
                self.assertIn(operator, source.OPERATORS["TRAIN"])
                self.assertIn(tuple(vector), source.VECTORS)
                self.assertEqual(p["demos"], n["demos"])
                self.assertEqual(len(p["demos"]), 24)
                self.assertEqual(sum(
                    source.relation(d["input_bits"], operator) !=
                    d["output_bits"] for d in p["demos"]), 3)
                # The independent source truth never becomes learner input.
                for d in p["demos"][:2]:
                    transformed = source.relation(d["input_bits"], operator)
                    restored = source.relation(transformed, operator, True)
                    self.assertEqual(restored, d["input_bits"])

    def test_ineligible_inputs_fail_closed(self):
        seed = source.COHORTS["Yggdrasil"]["TRAIN"].start
        with self.assertRaises(Exception):
            source.build("Yggdrasil", seed, [0, 0, 0], "TRAIN")
        with self.assertRaises(Exception):
            source.build("Wingless", seed, source.VECTORS[0], "TRAIN")


if __name__ == "__main__":
    unittest.main()
