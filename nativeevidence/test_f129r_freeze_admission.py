"""F129-R preimplementation source integrity, strongest baseline and authority tests."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f129r_freeze_admission as gate

class Admission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document,cls.sha256=gate.frozen()

    def reject(self,path,value):
        d=deepcopy(self.document)
        current=d
        for field in path[:-1]:
            current=current[field]
        current[path[-1]]=value
        with self.assertRaises(gate.Invalid):
            gate.validate(d)

    def test_original_negatives_and_exact_parent(self):
        self.assertEqual(len(self.sha256),64)
        self.assertEqual(self.document["negative_retention"]
                         ["F128R_Wingless_bit_access_ratio"],.53077508)
        self.assertFalse(self.document["negative_retention"]
                         ["F128R_walltime_success"])
        self.reject(("identity","parent_qualification_run"),0)
        self.reject(("negative_retention",
                     "F128R_Ubuntu_Wingless_walltime_ratio"),.5)

    def test_fast_native_baseline_and_walltime_cost_cannot_relax(self):
        d=deepcopy(self.document)
        d["hypothesis"]["comparison_controls"].remove(
            "CTRL_NATIVE_INDEXED_16_ELEMENT_VECTOR_EQUALITY")
        with self.assertRaises(gate.Invalid):
            gate.validate(d)
        self.reject(("qualification","maximum_median_walltime_ratio_to_native_indexed"),1.5)
        self.reject(("qualification","maximum_peak_allocated_memory_ratio_to_native_indexed"),10)
        self.reject(("qualification","measured_alternating_full_passes"),1)
        self.reject(("qualification","controls_all_eligible"),False)
        self.reject(("hypothesis","pack_and_index_cost_included"),False)

    def test_disjoint_source_cohorts_and_no_protected_use(self):
        self.reject(("source","lanes","Wingless","TRAIN_CHECK"),[240100,240115])
        self.reject(("source","lanes","Yggdrasil","CONFIRM"),[250116,250179])
        self.reject(("source","protected_confirmation_generated"),True)
        self.reject(("source","frozen_full_denominator_paired_cases_per_lane"),8)
        self.reject(("current_gate","generated_public_train_check_cases"),1)
        self.reject(("current_gate","generated_protected_confirm_cases"),1)

    def test_no_new_model_claim_or_privileged_external_runtime(self):
        self.reject(("hypothesis","one_candidate"),"POST_HOC_FASTEST")
        self.reject(("hypothesis","limits","maximum_candidate_expansions"),9999)
        self.reject(("current_gate","implementation_created"),True)
        self.reject(("current_gate","scientific_first_use"),True)
        self.reject(("current_gate","scientific_acceptance"),True)
        self.reject(("current_gate","optimizer_promotion"),True)
        self.reject(("current_gate","codex_calls"),1)
        self.reject(("current_gate","accepted_ref_mutations"),1)
        self.reject(("current_gate","ckb_plane_dependency"),True)

    def test_source_only_receipt_cannot_manufacture_science(self):
        receipt=gate.admission("a"*40)
        self.assertEqual(receipt["public_fit_cases_generated"],0)
        self.assertEqual(receipt["train_check_cases_generated"],0)
        self.assertEqual(receipt["protected_confirmation_cases_generated"],0)
        self.assertFalse(receipt["packed_join_implemented"])
        self.assertFalse(receipt["scientific_acceptance"])
        self.assertEqual(receipt["accepted_ref_mutations"],0)
        with self.assertRaises(gate.Invalid):
            gate.admission("forged")

if __name__=="__main__":
    unittest.main()
