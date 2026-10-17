"""F124-L exact forward bytecode and fixture-only first-use controls."""
import copy
import inspect
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124l_validation_only_adapter as adapter
import f124h_signed_evidence as original
import f124h_source as original_source
import f124h_train_receipt as original_train
import f124k_extended_source as fixture

class FixtureOnly(unittest.TestCase):
    def test_freeze_and_unchanged_original_model_bytecode(self):
        doc=adapter.frozen()
        self.assertEqual(adapter.FREEZE_BLOB,
                         "0280d0a669f68fb739833ec2f2e05a943b2124f1")
        self.assertFalse(doc["scientific_boundary"]["independent_first_use"])
        before=original.source.validate
        clone=adapter.original_arm_b_adapter()
        self.assertIs(clone.__code__,original.forward.__code__)
        self.assertIs(clone.__globals__["source"].validate,fixture.validate_public)
        self.assertIs(original.source.validate,before)
        self.assertIs(original.source,original_source)
        self.assertIs(adapter.fixed_12of16_adapter().__code__,
                      original_train.fixed_comparator.__code__)

    def test_fixture_only_reject_reserved_and_hidden_fields(self):
        for lane,seed in (("Wingless",180100),("Yggdrasil",190100),
                          ("Wingless",280024),("Yggdrasil",290024)):
            with self.assertRaises(adapter.Quarantined):
                adapter.fixture_pair(lane,seed,[1,1,2])
        positive,negative=adapter.fixture_pair("Wingless",280000,[1,1,2])
        self.assertEqual((len(positive["roles"]),len(negative["roles"])),(7,7))
        graph=copy.deepcopy(positive)
        graph["selected_route"]=1
        with self.assertRaises(fixture.Invalid):
            adapter.original_arm_b_adapter()(graph,original.initial("B"),"B")

    def test_readonly_fixture_predictions_without_training(self):
        weights=original.initial("B")
        samples,truth=adapter.evaluate_fixture("Wingless",280000,[1,1,2],weights)
        self.assertEqual(len(samples),2)
        self.assertEqual(truth["positive_symbolic_routes"],1)
        self.assertEqual(truth["negative_symbolic_routes"],0)
        for sample in samples:
            self.assertTrue(sample["failed"] or 0<=sample["probability"]<=1)
            if not sample["failed"]:
                self.assertIn("work",sample)
                self.assertIn("fixed_public_work",sample)

    def test_invalid_train_receipt_rejected_before_loading_weights(self):
        with self.assertRaises(adapter.Quarantined):
            adapter.authenticate_train_receipt(b'{"fake":"weights"}')
        with self.assertRaises(adapter.Quarantined):
            adapter.authenticate_train_receipt(b"")

    def test_original_input_contract_still_blocks_extended_fixture(self):
        p,n=adapter.fixture_pair("Wingless",280000,[1,1,2])
        with self.assertRaises(original_source.Invalid):
            original.forward(p,original.initial("B"),"B")
        self.assertTrue(callable(original.forward))
        self.assertEqual(original.EPOCHS,100)

if __name__=="__main__":
    unittest.main()
