"""F125-R graph family, protected cohort denial, label-blind invariants."""
from pathlib import Path
import copy,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f125r_train_environment as m

class GraphSource(unittest.TestCase):
    def test_train_cases_all_depths_and_identity(self):
        for lane,base in (("Wingless",100100),("Yggdrasil",101100)):
            for seed in (base,base+1,base+2):
                with self.subTest(lane=lane,seed=seed):
                    pos,neg=m.build(seed,[1,2,3],lane)
                    self.assertEqual(m.marginals(pos),m.marginals(neg))
                    self.assertEqual(m.graph_paths(pos,True),1)
                    self.assertEqual(m.graph_paths(neg,True),0)
                    self.assertEqual(m.graph_paths(pos),m.graph_paths(neg))
                    self.assertIn(m.graph_paths(pos),range(6,11))
                    self.assertIn(len(pos["roles"]),range(3,6))
                    self.assertEqual(m.build(seed,[1,2,3],lane),(pos,neg))
    def test_no_protected_seeds_or_f123_f124_sources(self):
        for lane,seed in (("Wingless",100200),("Yggdrasil",101200),
                          ("Wingless",98100),("Yggdrasil",99100)):
            with self.subTest(seed=seed),self.assertRaises(m.Invalid):
                m.build(seed,[1,2,3],lane)
    def test_order_invariance_of_labels(self):
        p,n=m.build(100100,[1,2,3],"Wingless")
        for graph,label in ((p,1),(n,0)):
            shuffled=copy.deepcopy(graph)
            shuffled["edges"].reverse()
            self.assertEqual(m.graph_paths(shuffled,True),label)
    def test_input_privilege_rejected(self):
        p,_=m.build(100100,[1,2,3],"Wingless")
        p["oracle_path"]=0
        with self.assertRaises(m.Invalid):m.validate(p)
    def test_all_train_not_selective_subset(self):
        rows=m.train_rows("Wingless",[[1,2,3],[3,1,2]])
        self.assertEqual(len(rows),128)
        with self.assertRaises(m.Invalid):
            m.train_rows("Wingless",[[1,2,3],[1,2,3]])

if __name__=="__main__":unittest.main()
