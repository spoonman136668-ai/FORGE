"""F128-R exact public token verifier and independent new source controls."""
from pathlib import Path
import copy,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f128r_train_environment as env
import f128r_bit_order_model as m

class NewMechanism(unittest.TestCase):
    def test_new_source_preserves_counterfactuals(self):
        for lane,seed in (("Wingless",220100),("Yggdrasil",230116)):
            stage="FIT" if seed==220100 else "TRAIN_CHECK"
            p,n=env.build(seed,[1,2,3],lane,stage)
            self.assertEqual(env.marginals(p),env.marginals(n))
            self.assertEqual(env.graph_paths(p,True),1)
            self.assertEqual(env.graph_paths(n,True),0)
            self.assertTrue(6<=env.graph_paths(p)<=12)
    def test_exact_verification_under_all_frozen_orders(self):
        pair=env.build(220100,[1,2,3],"Wingless","FIT")
        for g,correct in zip(pair,(1,0)):
            for order in (m.NATURAL,m.REVERSED,m.UNIFORM):
                observed,work=m.verify(g,order,trace=True)
                self.assertEqual(observed,correct)
                self.assertLessEqual(work["peak_states"],256)
                self.assertLessEqual(work["candidate_expansions"],512)
                self.assertGreater(work["bit_accesses"],0)
            self.assertEqual(m.verify(g,mode="native"),correct)
            shuffled=copy.deepcopy(g)
            shuffled["edges"].reverse()
            self.assertEqual(m.verify(shuffled,mode="native"),correct)
    def test_no_oracle_in_inference(self):
        p,_=env.build(220100,[1,2,3],"Wingless","FIT")
        with patch.object(env,"graph_paths",side_effect=AssertionError("oracle")):
            self.assertEqual(m.verify(p,m.NATURAL),1)
        p["oracle_true_path"]=1
        with self.assertRaises(env.Invalid):m.verify(p,m.NATURAL)
    def test_labels_not_required_to_fit(self):
        rows=env.cohort_rows("Wingless",[[1,2,3],[2,3,1]],"FIT")
        only_public=[g for g,y in rows]
        with patch.object(env,"graph_paths",side_effect=AssertionError("oracle")):
            order,train=m.fit(only_public)
        self.assertEqual(set(order),set(range(16)))
        self.assertEqual(train["fit_graphs"],64)
        self.assertFalse(train["labels_accessed"])
        with self.assertRaises(env.Invalid):m.fit(only_public[:-2])
    def test_train_check_never_fit_or_protected_constructed(self):
        with self.assertRaises(env.Invalid):
            env.build(220200,[1,2,3],"Wingless","FIT")
        with self.assertRaises(env.Invalid):
            env.build(230200,[1,2,3],"Yggdrasil","TRAIN_CHECK")
        with self.assertRaises(env.Invalid):
            env.build(180100,[1,2,3],"Wingless","FIT")
    def test_invalid_policy_rejected(self):
        p,_=env.build(220100,[1,2,3],"Wingless","FIT")
        with self.assertRaises(env.Invalid):m.verify(p,list(range(15)))
        with self.assertRaises(env.Invalid):m.verify(p,[0]*16)
        with self.assertRaises(env.Invalid):m.verify(p,mode="pretend-native")
if __name__=="__main__":unittest.main()
