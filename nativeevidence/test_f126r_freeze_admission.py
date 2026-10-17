"""Frozen F126-R source identity, strong comparator and autonomy guard tests."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f126r_freeze_admission as gate

class Freezing(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.contract,cls.source_sha=gate.frozen()
    def test_exact_source_identity_and_original_negative(self):
        self.assertEqual(len(self.source_sha),64)
        self.assertEqual(self.contract["retained_negatives"]["F125R_Wingless_paired"],[0,64])
        self.assertEqual(self.contract["retained_negatives"]["F125R_exact_public_symbolic_accuracy"],[64,64])
    def test_symbolic_baseline_cannot_be_discarded(self):
        c=deepcopy(self.contract)
        c["prospective_evaluation"]["frozen_controls"].remove("CTRL_EXACT_PUBLIC_SYMBOLIC_ELIGIBLE")
        with self.assertRaises(gate.Invalid): gate.validate(c)
        c=deepcopy(self.contract)
        c["prospective_evaluation"]["exact_symbolic_control"]="NON-ELIGIBLE CEILING"
        with self.assertRaises(gate.Invalid): gate.validate(c)
    def test_thresholds_costs_and_reserved_confirmation_stay_frozen(self):
        cases=[
            (("prospective_evaluation","accuracy_requirements","minimum_paired_fraction_of_exact"),.3),
            (("prospective_evaluation","cohorts","Wingless","CONFIRM"),[160100,160163]),
            (("hypothesis","trainable_parameters"),200),
            (("hypothesis","optimizer_epochs"),200),
            (("science_governance","protected_confirm_access"),True),
            (("science_governance","codex_calls"),1)]
        for keys,value in cases:
            c=deepcopy(self.contract)
            t=c
            for k in keys[:-1]:t=t[k]
            t[keys[-1]]=value
            with self.subTest(keys=keys),self.assertRaises(gate.Invalid):
                gate.validate(c)
    def test_source_only_receipt_does_not_manufacture_science(self):
        r=gate.admission("a"*40)
        self.assertEqual(r["train_cases_generated"],0)
        self.assertEqual(r["confirmation_cases_generated"],0)
        self.assertFalse(r["scientific_acceptance"])
        self.assertFalse(r["optimizer_promotion"])
        with self.assertRaises(gate.Invalid):gate.admission("unsafe")

if __name__=="__main__":unittest.main()
