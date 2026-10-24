"""No benchmark import or WebNLG/model execution: pinned L9 source arithmetic only."""
import copy
from pathlib import Path
import unittest

import l9_compute_parity_preflight as p

ROOT = Path(__file__).resolve().parent


class ParitySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = (ROOT / "l9_model_suite.py").read_bytes()
        cls.selector = (ROOT / "l9_neural_select_only.py").read_bytes()

    def test_original_pinned_sources_and_no_sci_go(self):
        report = p.audit(self.model, self.selector)
        self.assertEqual(report["model_source_git_blob"], p.SUITE_BLOB)
        self.assertEqual(report["selector_source_git_blob"], p.SELECT_BLOB)
        self.assertEqual(report["source_role_sha256"], p.ROLE_SHA)
        self.assertEqual(report["frozen_examples_per_epoch"], 2154)
        self.assertEqual(report["mandatory_seeds"], [1701, 1702])
        self.assertEqual(report["mandatory_epochs"], [4, 8, 12])
        self.assertFalse(report["scientific_quality_measured"])
        self.assertFalse(report["compute_or_energy_measured"])
        self.assertFalse(report["audit_dev_loaded"])
        self.assertFalse(report["official_test_loaded"])
        self.assertEqual(report["disposition"],
                         "SOURCE_STATIC_BENCHMARK_COST_PARITY_UNQUALIFIED")

    def test_exact_conditional_upper_bound(self):
        x = p.conditional_bounds(2154, 2, 3, 513)
        self.assertEqual(x["complete_evaluations"], 12924)
        self.assertEqual(x["max_forward_invocations_if_no_early_eos"], 6630012)
        self.assertEqual(x["max_cumulative_decoder_prefix_tokens_if_no_early_eos"],
                         1703913084)
        self.assertTrue(x["upper_bound_conditional_on_no_early_eos"])

    def test_guard_rejects_zero_negative_and_bool_counts(self):
        for counts in ((0, 2, 3, 513), (2154, -2, 3, 513),
                       (2154, True, 3, 513), (2154, 2, 0, 513)):
            with self.subTest(counts=counts), self.assertRaisesRegex(
                    ValueError, "L9_COMPUTE_PARITY_SOURCE_REJECT"):
                p.conditional_bounds(*counts)

    def test_rejects_mutated_transformer_source(self):
        s = self.model.decode("utf-8")
        for changed in ("self.forward(src, token)", "self._embed(src)",
                        "MAX_TARGET_BYTES = 512", "for _ in range(max_steps)"):
            self.assertIn(changed, s)
            bad = s.replace(changed, changed + " ", 1).encode()
            with self.subTest(changed=changed), self.assertRaisesRegex(
                    ValueError, "FROZEN_MODEL_BLOB_DRIFT"):
                p.audit(bad, self.selector)

    def test_rejects_mutated_selector_source(self):
        s = self.selector.decode("utf-8")
        for changed in ("for epoch in ALLOWED_EPOCHS",
                        "for ex in select", "model.MAX_TARGET_BYTES+1"):
            self.assertIn(changed, s)
            bad = s.replace(changed, changed + " ", 1).encode()
            with self.subTest(changed=changed), self.assertRaisesRegex(
                    ValueError, "FROZEN_SELECT_BLOB_DRIFT"):
                p.audit(self.model, bad)

    def test_source_is_static_and_has_no_science_access(self):
        code = (ROOT / "l9_compute_parity_preflight.py").read_text()
        self.assertNotIn("import torch", code)
        self.assertNotIn("import l9_model_suite", code)
        self.assertNotIn("import l9_train_select_candidate", code)
        self.assertNotIn("webnlg-dataset", code)
        self.assertNotIn("L9_AUDIT_DEV.json", code)


if __name__ == "__main__":
    unittest.main()
