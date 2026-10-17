"""F124-J public 12/14/16-bit comparators and fail-closed first-use readiness."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124h_source as graph
import f124h_train_receipt as original
import f124j_public_resource_preflight as audit

class F124JReadiness(unittest.TestCase):
    def pair(self):
        return graph.build(180000,[1,1,2],"Wingless","TRAIN")

    def test_pre_evaluation_frozen_identity_and_readonly_source_preflight(self):
        self.assertEqual(len(audit.freeze()),64)
        self.assertEqual(audit.FREEZE_BLOB,"c9131287cd30665f5928a15cab63bb7731eb6a78")
        p=audit.confirm_static_preflight()
        self.assertEqual(p["source_birth_capability"],"BLOCKED_SOURCE_NOT_IMPLEMENTED")
        self.assertEqual(p["claimed_reserved_hops"],[7,9])
        self.assertEqual(p["original_source_hops"],[4,5])
        self.assertEqual(p["reserved_examples_generated"],0)
        self.assertFalse(p["independent_first_use_authority_present"])

    def test_c12_reproduces_original_public_control_one_pair(self):
        for obs in self.pair():
            a,cost=audit.public_fixed_traversal(obs,12)
            b,old=original.fixed_comparator(obs)
            self.assertEqual(a,b)
            self.assertEqual(cost["public_edge_scans"],old["public_edge_scans"])
            self.assertEqual(cost["actual_raw_bit_comparisons"],old["bit_comparisons"])
            self.assertEqual(cost["actual_raw_bit_comparisons"],
                             16*cost["raw_token_pair_comparisons"])
            self.assertEqual(cost["algorithmic_weights"],0)

    def test_c16_exact_ceiling_but_not_retroactively_eligible(self):
        pos,neg=self.pair()
        results={}
        for threshold in audit.TOLERANCES:
            yes,work=audit.public_fixed_traversal(pos,threshold)
            no,other=audit.public_fixed_traversal(neg,threshold)
            results[threshold]=(yes,no)
            self.assertGreater(work["public_edge_scans"],0)
            self.assertGreater(other["public_edge_scans"],0)
        self.assertEqual(results[16],(True,False))
        self.assertEqual(graph.public_routes(pos),1)
        self.assertEqual(graph.public_routes(neg),0)

    def test_input_oracle_and_illegal_threshold_refused(self):
        p,_=self.pair()
        for threshold in (11,13,15,17,0,True):
            with self.subTest(threshold=threshold),self.assertRaises(graph.Invalid):
                audit.public_fixed_traversal(p,threshold)
        with self.assertRaises(graph.Invalid):
            audit.public_fixed_traversal(dict(p,selected_path=True),16)
        with self.assertRaises(graph.Invalid):
            graph.build(180100,[1,1,2],"Wingless","CONFIRM")

    def test_digest_fail_closed_on_modified_original(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"fake_report.json"
            file.write_text("{}")
            with self.assertRaisesRegex(graph.Invalid,"IMMUTABLE_F124I_REPORT_DIGEST"):
                audit.read_i_report(file)

    def test_full_train_control_all_original_strata_no_protected_input(self):
        for lane in graph.TRAIN:
            for seed in graph.TRAIN[lane]:
                p,n=graph.build(seed,[1,1,2],lane,"TRAIN")
                for threshold in audit.TOLERANCES:
                    self.assertTrue(audit.public_fixed_traversal(p,threshold)[0])
                self.assertTrue(audit.public_fixed_traversal(p,16)[0])
                self.assertFalse(audit.public_fixed_traversal(n,16)[0])
                self.assertEqual(len(p["roles"]),4+(seed%2))
                self.assertEqual(len(n["roles"]),len(p["roles"]))

if __name__=="__main__":
    unittest.main()
