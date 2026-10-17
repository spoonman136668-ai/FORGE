"""Adversarial source-only tests: no historical rewriting, baseline exclusion or protected first use."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f128r_freeze_admission as gate

class FrozenF128R(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract, cls.freeze_sha256 = gate.frozen()

    def mutate(self, fields, value):
        changed = deepcopy(self.contract)
        cursor = changed
        for field in fields[:-1]:
            cursor = cursor[field]
        cursor[fields[-1]] = value
        with self.assertRaises(gate.Invalid):
            gate.validate(changed)

    def test_parent_and_negative_are_pinned(self):
        self.assertEqual(gate.SOURCE_BLOB, "fb769675deb29235f96cefad50a87ab208d97950")
        self.assertEqual(len(self.freeze_sha256), 64)
        self.assertEqual(self.contract["negative_retention"]
                         ["F127R_Wingless_TRAIN_CHECK_paired"], [18, 32])
        self.assertEqual(self.contract["negative_retention"]
                         ["F127R_eligible_exact_paired_both_lanes"], [32, 32])
        self.mutate(("identity", "parent_exact_head_ci_run"), 1)
        self.mutate(("negative_retention", "F127R_Wingless_saved_cost_ratio_to_indexed_exact"), 0.5)

    def test_mandatory_fast_exact_baseline(self):
        x = deepcopy(self.contract)
        x["controls"]["frozen_controls"].remove(
            "CTRL_OPTIMIZED_INDEXED_EXACT_VECTOR_EQUALITY")
        with self.assertRaises(gate.Invalid):
            gate.validate(x)
        self.mutate(("controls", "mandatory_eligible_exact"),
                    "A slower intentionally unindexed scanner is the only control")
        self.mutate(("controls", "cost", "maximum_median_walltime_ratio_to_optimized_exact"), 12)
        self.mutate(("controls", "cost", "maximum_bit_comparison_ratio_to_full_16_reference"), 1)
        self.mutate(("controls", "cost", "measured_interleaved_complete_passes"), 1)
        self.mutate(("controls", "cost", "native_vector_comparison_is_eligible_even_if_it_outperforms_learned"), False)

    def test_train_check_and_protected_no_leakage(self):
        self.mutate(("source", "lanes", "Wingless", "TRAIN_CHECK"), [220100, 220115])
        self.mutate(("source", "lanes", "Yggdrasil", "CONFIRM"), [230116, 230179])
        self.mutate(("source", "protected_CONFIRM_generated"), True)
        self.mutate(("source", "no_seed_reselection_after_scoring"), False)
        self.mutate(("hypothesis", "trainable_statistics"), 220)
        self.mutate(("hypothesis", "boundaries", "maximum_candidate_expansions"), 2048)
        self.mutate(("hypothesis", "no_calibration_or_threshold"), False)

    def test_governance_and_original_denied(self):
        self.mutate(("scope", "scientific_first_use"), True)
        self.mutate(("scope", "scientific_acceptance"), True)
        self.mutate(("scope", "optimizer_promotion"), True)
        self.mutate(("scope", "codex_calls"), 1)
        self.mutate(("scope", "paid_inference_calls"), 1)
        self.mutate(("scope", "accepted_ref_mutations"), 1)
        self.mutate(("scope", "ckb_plane_dependency"), True)
        self.mutate(("scope", "mind_palace_writes"), 1)

    def test_only_source_receipt_authorized(self):
        r = gate.source_receipt("a"*40)
        self.assertEqual(r["fit_cases_generated"], 0)
        self.assertEqual(r["train_check_cases_generated"], 0)
        self.assertEqual(r["protected_confirm_generated"], 0)
        self.assertFalse(r["learned_bit_order_fitted"])
        self.assertFalse(r["scientific_acceptance"])
        self.assertFalse(r["optimizer_promotion"])
        self.assertEqual(r["accepted_ref_mutations"], 0)
        with self.assertRaises(gate.Invalid):
            gate.source_receipt("forged")

if __name__ == "__main__":
    unittest.main()
