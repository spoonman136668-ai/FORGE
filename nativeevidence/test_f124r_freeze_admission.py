"""F124-R bounded freeze tests. No graph sampling, training, or first-use."""
from copy import deepcopy
import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import f124r_freeze_admission as gate


class F124RFreeze(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.digest = gate.frozen()

    def test_exact_identity_and_parent_negative(self):
        self.assertEqual(len(self.digest), 64)
        self.assertEqual(gate.EXPECTED_FREEZE_BLOB,
                         "891c950e1d25eea90fbe5191abf8e9c1ab4eac7f")
        self.assertFalse(self.cfg["parent"]["f123_train_outcome"]["Wingless"]
                         ["meets_frozen_margin"])

    def test_changed_science_thresholds_quarantine(self):
        for key, value in (("frozen_success_margin_absolute", 0.04),
                           ("max_relative_s2_operations_to_dense_b", 1.0),
                           ("resource_reduction_must_hold_each_lane", False)):
            mutated = deepcopy(self.cfg)
            mutated["evaluation"][key] = value
            with self.subTest(key=key), self.assertRaises(gate.Invalid):
                gate.validate(mutated)

    def test_reserved_seed_and_hidden_feature_mutations_quarantine(self):
        changes = [
            lambda o: o["cohorts"].update(confirm_is_reserved=False),
            lambda o: o["cohorts"]["Wingless"].update(
                CONFIRM=[98100, 98163]),
            lambda o: o["environment"].update(
                no_engineered_true_path_or_equality=False),
            lambda o: o["authority"].update(no_new_scheduler=False),
            lambda o: o["parent"].update(f123_exact_head="0" * 40),
            lambda o: o["proposed_mechanism"].update(beam_width=9)
        ]
        for update in changes:
            mutated = deepcopy(self.cfg)
            update(mutated)
            with self.subTest(update=update), self.assertRaises(gate.Invalid):
                gate.validate(mutated)

    def test_source_receipt_is_read_only_preimplementation(self):
        r = gate.receipt("f" * 40)
        self.assertEqual(r["cohorts_read"], 0)
        self.assertFalse(r["learned_model_implemented"])
        self.assertFalse(r["protected_confirmation_read"])
        self.assertFalse(r["optimizer_promotion"])
        self.assertFalse(r["accepted_ref_mutation"])
        with self.assertRaises(gate.Invalid):
            gate.receipt("unsafe")

if __name__ == "__main__":
    unittest.main()
