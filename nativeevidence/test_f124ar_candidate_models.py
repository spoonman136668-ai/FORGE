"""F124-AR engineering tests use synthetic public supports or previously
consumed F124-AQ TRAIN fixtures, NEVER prospective new F124-AR TRAIN/DEV.
No science result, selection or reserved-source first-use is produced.
"""
import inspect
import math
import unittest

import f124ar_cross_task_relations as y
import f124ar_packed_causal_calibration as w
import f124aq_train_source as prior_source
import f124am_terminal_competition as original

BASE = [.6, .7, .9, .5, .85, .15, -.55]
YDELTA = [.05, -.03]
WDELTA = [.05, -.03, .02, -.04]


def public_demos(shift):
    rows = []
    for j in range(24):
        bits = [((j * 29 + i * 7 + shift) >> (i % 5)) & 1
                for i in range(16)]
        targets = [bits[(i + shift) % 16] for i in range(16)]
        rows.append({"output_bits": bits, "input_bits": targets})
    return rows


class NewModelsFocused(unittest.TestCase):
    def test_all_six_ygg_candidate_training_and_full_storage_census(self):
        src = inspect.getsource(y)
        for blocked in ("import f124ar_train_source",
                        "import f124aq_train_source",
                        "source.plain(",
                        "source.relation(",
                        "source_truth",
                        "inverse_output("):
            self.assertNotIn(blocked, src)
        for mode in y.MODES:
            for width in y.WIDTHS:
                model = y.train_shared(
                    [public_demos(0), public_demos(1)], mode, width)
                self.assertEqual(model["shared_parameters"], 32 * width)
                self.assertEqual(model["shared_float_storage_bytes_lower"],
                                 32 * width * 8)
                self.assertEqual(model["public_fit_per_task"], 20)
                self.assertEqual(model["public_check_per_task"], 4)
                self.assertFalse(model["source_oracle_used"])
                self.assertFalse(model["operator_catalog_known"])
                pred = y._estimate(model, public_demos(2)[0]["output_bits"],
                                   public_demos(2)[:20])
                self.assertEqual(len(pred), 16)
                self.assertTrue(all(math.isfinite(v) for v in pred))
                self.assertEqual(model["width"], width)
                self.assertGreater(model["training_operations_upper"], 0)

    def test_existing_source_ygg_no_new_train_or_dev_consumed(self):
        prior_source.frozen()
        seed = prior_source.COHORTS["Yggdrasil"]["TRAIN"].start
        _, _, _, positive, negative, _ = prior_source.build(
            "Yggdrasil", seed, prior_source.VECTORS[0], "TRAIN")
        for mode in y.MODES:
            model = y.train_shared([public_demos(0)], mode, 8)
            for graph in (positive, negative):
                score, original_work, census = y.ygg(
                    graph, BASE, YDELTA, model)
                self.assertTrue(math.isfinite(score))
                self.assertEqual(census["mode"], mode)
                self.assertEqual(census["public_fit"], 20)
                self.assertEqual(census["public_check"], 4)
                self.assertTrue(census["extra_task_working_storage_disclosed"])
                self.assertEqual(census["max_original_cognitive_cells"], 16)
                self.assertFalse(census["source_oracle_used"])
                self.assertGreater(census["shared_float_bytes_lower"], 0)
                if original_work is not None:
                    self.assertLessEqual(original_work["max_active"], 7)
                    self.assertLessEqual(original_work["max_retained"], 9)

    def test_one_packet_baseline_identity_and_two_candidate_families(self):
        src = inspect.getsource(w)
        self.assertNotIn("import f124ar_train_source", src)
        self.assertNotIn("inverse_output(", src)
        prior_source.frozen()
        seed = prior_source.COHORTS["Wingless"]["TRAIN"].start
        _, operator, nonce, pos, neg, _ = prior_source.build(
            "Wingless", seed, prior_source.VECTORS[0], "TRAIN")
        graphs = (
            prior_source.plain(pos, operator, nonce),
            prior_source.plain(neg, operator, nonce))
        # Synthetic repeated already-consumed prior TRAIN public graphs;
        # training API itself is isolated from the fresh AR TRAIN/DEV cohorts.
        artificial_prior_cases = [
            ("public-synthetic-" + str(i), "existing-fixture",
             graphs[0], graphs[1]) for i in range(48)]
        learned = w.fit_calibration(artificial_prior_cases)
        self.assertEqual(learned["train_pairs"], 48)
        self.assertEqual(learned["global_parameters"], 5)
        self.assertEqual(len(learned["likelihood_log_ratio"]), 5)
        self.assertFalse(learned["source_inverse_in_model"])
        for graph in graphs:
            control, baseline_work = original.terminal_competitive(
                graph, BASE, WDELTA, 0.)
            actual, work = w.score(
                graph, BASE, WDELTA, "original_gamma0", 0.)
            self.assertEqual(control, actual)
            self.assertEqual(work["edge_inspections"],
                             baseline_work["edge_inspections"])
            for mode in w.MODES[1:]:
                for penalty in w.ALPHAS[1:]:
                    got, census = w.score(
                        graph, BASE, WDELTA, mode, penalty,
                        calibration=learned if mode ==
                        "train_calibrated_hop_likelihood" else None)
                    self.assertTrue(math.isfinite(got))
                    self.assertEqual(census["max_states_per_node"], 1)
                    self.assertEqual(census["max_packed_bits_per_state"], 12)
                    self.assertLessEqual(census["max_active"], 64)
                    self.assertEqual(census["extra_retained_states"], 0)
                    self.assertFalse(census["source_oracle_in_model"])
                    self.assertGreater(census["extra_hop_evidence_ops"], 0)
        with self.assertRaises(Exception):
            w.score(graphs[0], BASE, WDELTA,
                    "train_calibrated_hop_likelihood", .02)
        with self.assertRaises(Exception):
            w.score(graphs[0], BASE, WDELTA, "invalid", .02)

    def test_bounded_training_and_qualifier_inputs(self):
        with self.assertRaises(Exception):
            y.train_shared([public_demos(1)], "unknown", 8)
        with self.assertRaises(Exception):
            y.train_shared([public_demos(1)], y.MODES[0], 32)
        with self.assertRaises(Exception):
            y.train_shared([public_demos(1)[:20]], y.MODES[0], 8)
        with self.assertRaises(Exception):
            w.fit_calibration([])


if __name__ == "__main__":
    unittest.main()
