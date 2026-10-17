"""F125-R source-only tamper gates; no TRAIN or CONFIRM generated."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f125r_freeze_admission as gate

class SourceFreeze(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.digest=gate.frozen()
    def test_exact_freeze(self):
        self.assertEqual(len(self.digest),64)
        self.assertEqual(gate.FROZEN_BLOB,"0a2030f17123b7e096c42e730f3a536f014275bd")
    def test_negative_history_not_rewritten(self):
        x=deepcopy(self.cfg)
        x["negative_evidence"]["F124R_Wingless"]["best_fixed"]=40
        with self.assertRaises(gate.Invalid):gate.validate(x)
    def test_headroom_and_success_not_loosened(self):
        for path,val in [
            (("evaluation","headroom_eligibility",
              "minimum_TRAIN_ceiling_minus_best_fixed_fraction"),0.02),
            (("evaluation","minimum_absolute_paired_gain_per_lane"),0.01),
            (("evaluation","resource",
              "maximum_s2_successor_primitive_operations_fraction_of_dense"),1.0),
            (("cohorts","confirm_reserved"),False),
            (("cohorts","Wingless","CONFIRM"),[100100,100163]),
            (("mechanism","no_topk_pruning"),False),
            (("mechanism","maximum_active_states_per_hop"),2)
        ]:
            x=deepcopy(self.cfg)
            y=x
            for field in path[:-1]:y=y[field]
            y[path[-1]]=val
            with self.subTest(path=path),self.assertRaises(gate.Invalid):
                gate.validate(x)
    def test_unauthorized_science_denied(self):
        for k in ("scientific_first_use","optimizer_promotion"):
            x=deepcopy(self.cfg)
            x["authority"][k]=True
            with self.assertRaises(gate.Invalid):gate.validate(x)
    def test_receipt_never_claims_training(self):
        proof=gate.receipt("f"*40)
        self.assertEqual(proof["graph_cases_generated"],0)
        self.assertFalse(proof["model_trained"])
        self.assertFalse(proof["protected_confirmation_read"])
        with self.assertRaises(gate.Invalid):gate.receipt("not a SHA")

if __name__=="__main__":unittest.main()
