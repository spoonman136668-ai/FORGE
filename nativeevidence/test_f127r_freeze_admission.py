"""F127-R preimplementation freeze immutable negative and control denial."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f127r_freeze_admission as gate

class Admission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source,cls.digest=gate.frozen()
    def test_exact_parent_freeze_and_negative_retention(self):
        self.assertEqual(len(self.digest),64)
        self.assertEqual(gate.FREEZE_BLOB,
                         "0fde790b95384aaf19e9725ea5a82e7819407c3d")
        self.assertEqual(self.source["retained_negatives"]
                         ["F126R_no_null_ablation_paired_Wingless"],[0,64])
    def test_strong_symbolic_eligible(self):
        p=deepcopy(self.source)
        p["frozen_comparison"]["fixed_controls"].remove(
            "CTRL_EXACT_PUBLIC_SYMBOLIC_ELIGIBLE")
        with self.assertRaises(gate.Quarantined):gate.validate(p)
        p=deepcopy(self.source)
        p["frozen_comparison"]["eligible_exact_symbolic"]="Excluded ceiling"
        with self.assertRaises(gate.Quarantined):gate.validate(p)
    def test_no_leakage_nor_posthoc_threshold_tuning(self):
        cases=[
            (("source_cohorts","Wingless","TRAIN_CHECK"),[180100,180115]),
            (("source_cohorts","Wingless","CONFIRM"),[180200,180220]),
            (("hypothesis","training","output_threshold"),.4),
            (("hypothesis","training","epochs"),200),
            (("hypothesis","safety","exclude_pair_partner_at_inference"),False),
            (("frozen_comparison","minimum_paired_correct_fraction_of_exact"),.5),
            (("cost_verification","target_cost_ratio_to_exact"),1.2),
            (("current_gate","scientific_first_use"),True),
            (("current_gate","codex_calls"),1),
        ]
        for path,value in cases:
            p=deepcopy(self.source)
            x=p
            for field in path[:-1]:x=x[field]
            x[path[-1]]=value
            with self.subTest(path=path),self.assertRaises(gate.Quarantined):
                gate.validate(p)
    def test_zero_original_science_and_sha_bound(self):
        evidence=gate.receipt("e"*40)
        self.assertEqual(evidence["public_fit_cases_generated"],0)
        self.assertEqual(evidence["protected_confirm_cases_generated"],0)
        self.assertFalse(evidence["trained_weights_created"])
        self.assertFalse(evidence["scientific_acceptance"])
        self.assertEqual(evidence["accepted_ref_mutations"],0)
        with self.assertRaises(gate.Quarantined):
            gate.receipt("forged")
if __name__=="__main__":
    unittest.main()
