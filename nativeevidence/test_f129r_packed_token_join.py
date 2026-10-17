"""F129-R public-only FIT/CHECK, exact join, indexed native equality and tamper."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f129r_train_environment as env
import f129r_packed_token_join as model

class PackedJoin(unittest.TestCase):
    def test_fresh_balanced_family_and_disjoint_splits(self):
        for lane in ("Wingless","Yggdrasil"):
            a=env.cohort_rows(lane,[[1,2,3],[2,3,1]],"FIT")
            b=env.cohort_rows(lane,[[1,2,3],[2,3,1]],"TRAIN_CHECK")
            self.assertEqual((len(a),len(b)),(64,64))
            self.assertEqual((sum(y for g,y in a),sum(y for g,y in b)),(32,32))
            self.assertFalse(set(env.digest(g) for g,y in a)&
                             set(env.digest(g) for g,y in b))
            for k in range(0,64,2):
                p,y=a[k];n,ny=a[k+1]
                self.assertEqual((y,ny),(1,0))
                self.assertEqual(env.marginals(p),env.marginals(n))
                self.assertEqual(env.graph_paths(p,True),1)
                self.assertEqual(env.graph_paths(n,True),0)

    def test_full_exact_comparator_and_edge_permutation(self):
        for lane,seed in (("Wingless",240100),("Yggdrasil",250116)):
            stage="FIT" if lane=="Wingless" else "TRAIN_CHECK"
            pos,neg=env.build(seed,[1,2,3],lane,stage)
            for graph,label in ((pos,1),(neg,0)):
                for method in model.METHODS:
                    value,work=model.invoke(graph,method,True)
                    self.assertEqual(value,label)
                    self.assertLessEqual(work["peak_states"],256)
                    self.assertLessEqual(work["state_allocations"],512)
                    revised=copy.deepcopy(graph);revised["edges"].reverse()
                    self.assertEqual(model.invoke(revised,method),label)
    def test_no_oracle_access_on_inference(self):
        p,_=env.build(240100,[1,2,3],"Wingless","FIT")
        with patch.object(env,"graph_paths",side_effect=AssertionError("oracle read")):
            for name in model.METHODS:
                self.assertEqual(model.invoke(p,name),1)
        p["selected_true_path"]=0
        with self.assertRaises(env.Invalid):
            model.invoke(p,model.METHODS[3])

    def test_packing_uses_sixteen_public_raw_bits_only(self):
        self.assertEqual(model.pack([1]+[0]*15),1)
        self.assertEqual(model.pack([0]*15+[1]),32768)
        self.assertEqual(model.pack([1]*16),65535)
        p,_=env.build(240100,[1,2,3],"Wingless","FIT")
        p["edges"][0]["src_bits"][0]=2
        with self.assertRaises(env.Invalid):
            model.invoke(p,model.METHODS[3])

    def test_no_protected_and_retrospective_source(self):
        for lane,seed in (("Wingless",240200),("Yggdrasil",250200),
                          ("Wingless",220100),("Yggdrasil",230100)):
            for phase in ("FIT","TRAIN_CHECK"):
                with self.assertRaises(env.Invalid):
                    env.build(seed,[1,2,3],lane,phase)

    def test_four_strong_controls_no_denominator_dropped(self):
        rows=env.cohort_rows("Wingless",[[1,2,3],[2,3,1]],"TRAIN_CHECK")
        result=model.compare(rows)
        self.assertEqual(set(result),set(model.METHODS))
        for info in result.values():
            self.assertEqual(info["paired_correct"],32)
            self.assertEqual(info["positive_correct"],32)
            self.assertEqual(info["negative_correct"],32)
        with self.assertRaises(env.Invalid):
            model.compare(rows[:-2])
if __name__=="__main__":unittest.main()
