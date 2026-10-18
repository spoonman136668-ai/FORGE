"""F124-AT preregistered source and diagnostic scoring focused qualification.

Run no new F124-AT TRAIN election, no new DEV, no optimizer promotion.
One previously consumed F124-AS TRAIN graph may test source-blind state bounds.
"""
import inspect
import math
import unittest
from collections import Counter

import f124at_train_source as source
import f124at_train_evidence as evidence
import f124at_packed_collision_controls as packed
import f124as_train_source as previous
import f124am_terminal_competition as original

BASE = [.6, .7, .9, .5, .85, .15, -.55]
WDELTA = [.05, -.03, .02, -.04]


class F124ATFrozenSource(unittest.TestCase):
    def test_exact_source_ancestry_and_no_dev(self):
        freeze = source.frozen()
        self.assertEqual(source.witness.blob(source.FREEZE),
                         "45dca352cd732358b1dd02b05bf9661c4ed37dc5")
        self.assertEqual(source.witness.blob(previous.__file__),
                         "7b20f61d7f4257f76297f173e3c8805b8ace88ef")
        self.assertEqual(
            freeze["lineage"]["qualified_parent"],
            "449fc54cecccb6e30eaa13016f9d1828532714ac")
        self.assertTrue(all(not value for value in
                            freeze["authority"].values()))
        self.assertTrue(set(source.OPERATORS["TRAIN"]).isdisjoint(
            source.OPERATORS["DEV"]))
        for lane in source.COHORTS:
            self.assertTrue(set(source.COHORTS[lane]["TRAIN"]).isdisjoint(
                source.COHORTS[lane]["DEV"]))
            with self.assertRaises(Exception):
                source.pairs(lane, "DEV")
            with self.assertRaises(Exception):
                source.build(lane, source.COHORTS[lane]["DEV"].start,
                             source.VECTORS[0], "DEV")

    def test_new_pair_denominators_without_scientific_screening(self):
        # Source-only truth and denominator; never select/train a candidate.
        for lane in ("Yggdrasil", "Wingless"):
            rows = source.pairs(lane, "TRAIN")
            self.assertEqual(len(rows), 48)
            self.assertEqual(Counter(x[2] for x in rows),
                             Counter({f: 12 for f in source.FAMILIES}))
            self.assertEqual(sum(source.relation(d["input_bits"], op) !=
                                 d["output_bits"] for _, _, _, op, _, p, _
                                 in rows for d in p["demos"]), 48 * 3)
            self.assertTrue(all(p["demos"] == n["demos"]
                                for _, _, _, _, _, p, n in rows))

    def test_original_checksum_and_overbudget_separation(self):
        self.assertEqual(tuple(packed.CHECKSUMS), (
            "original_gamma0_checksum_1342",
            "fixed_12bit_checksum_1234",
            "fixed_12bit_checksum_2413"))
        # Previously consumed AS TRAIN only, not fresh AT research results.
        seed = previous.COHORTS["Wingless"]["TRAIN"].start
        _, op, nonce, pos, neg, _ = previous.build(
            "Wingless", seed, previous.VECTORS[0], "TRAIN")
        for graph in (previous.plain(pos, op, nonce),
                      previous.plain(neg, op, nonce)):
            control, ow = original.terminal_competitive(
                graph, BASE, WDELTA, 0.)
            baseline, work = packed.score12(
                graph, BASE, WDELTA,
                "original_gamma0_checksum_1342")
            self.assertEqual(control, baseline)
            self.assertEqual(ow["edge_inspections"],
                             work["edge_inspections"])
            for arm in packed.CHECKSUMS:
                score, counters = packed.score12(
                    graph, BASE, WDELTA, arm)
                self.assertTrue(math.isfinite(score))
                self.assertEqual(counters["max_states_per_node"], 1)
                self.assertEqual(counters["max_packed_bits_per_state"], 12)
                self.assertLessEqual(counters["max_active"], 64)
                self.assertEqual(counters.get("max_encoded_cache", 0), 0)
                self.assertTrue(packed.collisions(
                    graph, packed.CHECKSUMS[arm])["collision_pairs"] >= 0)
            value, diag = packed.full16_diagnostic(
                graph, BASE, WDELTA)
            self.assertTrue(math.isfinite(value))
            self.assertEqual(diag["max_packed_bits_per_state"], 16)
            self.assertTrue(diag["overbudget_only"])
        with self.assertRaises(Exception):
            packed.score12(graph, BASE, WDELTA, "not_preregistered")

    def test_source_oracle_only_in_evaluator(self):
        for module in (packed,):
            code = inspect.getsource(module)
            self.assertNotIn("import f124at_train_source", code)
            self.assertNotIn("source.plain(", code)
        self.assertEqual(evidence.rank17([
            {"input_bits": [int(i == j) for j in range(16)]}
            for i in range(16)]), 16)


if __name__ == "__main__":
    unittest.main()
