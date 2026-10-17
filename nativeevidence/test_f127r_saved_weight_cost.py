"""F127-R saved-weight cost source integrity and exact public reference."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f127r_saved_weight_cost as audit
import f127r_train_environment as env
class AuditedCost(unittest.TestCase):
    def test_public_indexed_reference_matches_true_pair(self):
        for lane,seed in (("Wingless",180100),("Yggdrasil",190116)):
            stage="FIT" if seed==180100 else "TRAIN_CHECK"
            p,n=env.build(seed,[1,2,3],lane,stage)
            for graph,label in ((p,1),(n,0)):
                value,work=audit.exact_indexed(graph)
                self.assertEqual(value,label)
                self.assertEqual(value,int(env.graph_paths(graph,True)>0))
                self.assertGreater(work["indexed_edges"],0)
                self.assertGreater(work["edge_visits"],0)
    def test_no_unseen_source_eligibility(self):
        with self.assertRaises(env.Invalid):
            env.build(180200,[1,2,3],"Wingless","FIT")
        self.assertEqual(audit.SAVED_SHA,
            "6ff85a82acca1fb0f57495c277fd5ed764670c9e")
    def test_receipt_hash_is_frozen_to_original(self):
        self.assertEqual(audit.REPORT_HASH,
            "7e784f77a78aa0e7def04fcb8024b69a9ec392e6a13a720924dbe78d40528a45")
if __name__=="__main__":unittest.main()
