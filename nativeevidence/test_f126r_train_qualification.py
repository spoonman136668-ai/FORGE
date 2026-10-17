"""F126-R public strong controls and no-result-censorship tests."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f126r_train_qualification as m
import f126r_train_environment as env
import f126r_contrastive_model as model
class Controls(unittest.TestCase):
    def test_public_exact_eligible_ceiling_and_cost_receipt(self):
        pos,neg=env.build(160100,[1,2,3],"Wingless")
        for graph,label in ((pos,1),(neg,0)):
            score,work=m.oracle_work(graph)
            self.assertEqual(score,label)
            self.assertGreater(work["edge_scans"],0)
            self.assertGreater(work["state_allocations"],0)
    def test_strong_frozen_dense_source_identity(self):
        self.assertEqual(m.git_blob(m.dense.__file__),m.F123_BLOB)
        self.assertEqual(m.git_blob(m.preserving.__file__),m.F125R_BLOB)
    def test_incompatible_sparse_interface_is_not_silently_extended(self):
        p,n=env.build(160102,[1,2,3],"Wingless")
        self.assertEqual(len(p["roles"]),5)
        with self.assertRaises(Exception):
            m.sparse2.forward(p,m.sparse2.init())
    def test_no_confirmation_constructor_or_forged_source(self):
        with self.assertRaises(env.Invalid):
            env.build(160200,[1,2,3],"Wingless")
        with self.assertRaises(env.Invalid):
            m.experiment({"schema":"forged"},"notsha")
if __name__=="__main__":
    unittest.main()
