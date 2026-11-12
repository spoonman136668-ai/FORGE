"""Fail-closed offline contract tests for ACC-95 (not scientific qualification)."""
import unittest
from fitdev import (
    CountTable, FIT_RULES, DEV_RULES, FIT_SEEDS, DEV_SEEDS,
    next_bit, seed_for, transitions, baseline_screen,
)

class Contracts(unittest.TestCase):
    def test_source_partitions_and_reserved_rejection(self):
        self.assertFalse(set(FIT_RULES) & set(DEV_RULES))
        self.assertFalse(set(FIT_SEEDS) & set(DEV_SEEDS))
        for split, rule, seed in (("TEST", 22, 809), ("DEV", 22, 701),
                                  ("FIT", 90, 809), ("DEV", 90, 701)):
            with self.assertRaises(ValueError):
                seed_for(split, rule, seed, 0)

    def test_deterministic_trace_and_disjoint_visible_queries(self):
        a = transitions("FIT", 90, 601, width=25)
        b = transitions("FIT", 90, 601, width=25)
        self.assertEqual(a["trace_sha256"], b["trace_sha256"])
        for row in a["records"]:
            self.assertEqual(len(row["visible"]), 6)
            self.assertEqual(len(row["queries"]), 19)
        self.assertNotEqual(a["trace_sha256"],
                            transitions("FIT", 110, 601, width=25)["trace_sha256"])

    def test_rule_bits_and_length_guards(self):
        for idx in range(8):
            bits = ((idx >> 2) & 1, (idx >> 1) & 1, idx & 1)
            self.assertEqual(next_bit(90, *bits), (90 >> idx) & 1)
        with self.assertRaises(ValueError):
            transitions("FIT", 90, 601, width=12)

    def test_table_restart_and_invalid_snapshot(self):
        t = CountTable.fresh()
        t.observe([((1, 0, 1), 1)] * 3)
        copy = CountTable.restore(t.snapshot())
        self.assertEqual(copy.snapshot(), t.snapshot())
        self.assertEqual(copy.predict((1, 0, 1)), 1)
        with self.assertRaises(ValueError):
            CountTable.restore('{"positive":[-1],"negative":[]}')
        copy.observe([((1, 0, 1), 0)])
        self.assertNotEqual(copy.snapshot(), t.snapshot())

    def test_fit_dev_nonadmission(self):
        for split, rule, seed in (("FIT", 90, 601), ("DEV", 54, 701)):
            result = baseline_screen(split, rule, seed)
            self.assertEqual(result["queries"], 128 * 19)
            self.assertFalse(result["science_accepted"])
            self.assertFalse(result["test_split_accessed"])
            self.assertFalse(result["resources_qualified"])
            self.assertTrue(0 <= result["accuracy"] <= 1)

if __name__ == "__main__":
    unittest.main()
