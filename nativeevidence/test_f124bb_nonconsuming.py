"""F124-BB non-consuming source and exact matched-joint preservation tests."""
import ast
import unittest
from pathlib import Path
import f124bb_train_source as source
import f124bb_fit_screen as science
import f124bb_public_consensus as consensus

class BBPreflight(unittest.TestCase):
    def test_frozen_source_and_no_DEV(self):
        d=source.frozen()
        self.assertEqual(d["lineage"]["parent_archived_head"],source.PARENT)
        self.assertEqual(d["information"]["public_FIT"],40)
        self.assertEqual(d["information"]["public_CHECK"],8)
        self.assertEqual(d["sources"]["FIT_seeds"],[5000000,5000011])
        self.assertEqual(d["sources"]["SCREEN_seeds"],[5000012,5000023])
        self.assertEqual(len(d["models"]["new_candidates"]),4)
        self.assertTrue(all(x is False for x in d["governance"].values()))
        with self.assertRaises(Exception):source.build(5000100,source.VECTORS[0])
        with self.assertRaises(Exception):source.rows("DEV")

    def test_no_accepted_positive_loss_allowed_even_with_FP_reduction(self):
        def mk(positives,fp,paired,feistel):
            return {"accepted_positive_case_ids":positives,
                    "FP":fp,"paired":paired,
                    "by_operator":{"feistel":{"paired":feistel}}}
        joint=mk(["aff","feistel","feistel2"],1,3,2)
        veto=mk(["aff","feistel"],0,2,1)
        cards={"joint_balanced48":joint,"consensus_balanced_eta0":veto}
        ok,details=science.eligibility(cards,"consensus_balanced_eta0")
        self.assertFalse(ok)
        self.assertFalse(details["all_joint_accepted_positive_ids_retained"])
        cards["consensus_balanced_eta0"]=mk(["aff","feistel","feistel2"],0,3,2)
        ok,details=science.eligibility(cards,"consensus_balanced_eta0")
        self.assertTrue(ok)
        self.assertEqual(details["preserved_joint_accepted_positive_ids"],3)
        cards["joint_balanced48"]["FP"]=0
        ok,details=science.eligibility(cards,"consensus_balanced_eta0")
        self.assertFalse(ok)
        self.assertFalse(details["strictly_reduced_joint_false_positives"])

    def test_consensus_uses_public_graph_not_oracle(self):
        code=(Path(__file__).resolve().parents[0]/"f124bb_public_consensus.py").read_text()
        tree=ast.parse(code)
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
        self.assertFalse(any("f124bb_train_source" in s or "f124ao_frozen_source" in s for s in imports))
        self.assertNotIn("source.relation",code)
        self.assertNotIn("source.plain",code)
        self.assertEqual(consensus.ETAS,(0.,.2))

if __name__=="__main__":unittest.main()
