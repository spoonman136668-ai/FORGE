"""F124-R graph source TRAIN invariants."""
from pathlib import Path
import copy, sys, unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124r_train_environment as env

class Source(unittest.TestCase):
    def test_construct_train_pair(self):
        for lane, seed in (("Wingless",98100),("Wingless",98101),("Yggdrasil",99100),("Yggdrasil",99101)):
            p,n=env.build(seed,[1,1,2],lane)
            self.assertEqual(set(p),env.FIELDS)
            self.assertTrue(all(set(e)==env.EDGE_FIELDS for e in p["edges"]))
            self.assertEqual(env.marginals(p),env.marginals(n))
            self.assertEqual(env.symbolic_count(p),1)
            self.assertEqual(env.symbolic_count(n),0)
            self.assertGreaterEqual(env.symbolic_count(p,True),4)
            self.assertEqual(env.build(seed,[1,1,2],lane),(p,n))
    def test_reverse_order_keeps_label(self):
        p,n=env.build(98102,[3,2,0],"Wingless")
        for graph,label in ((p,1),(n,0)):
            changed=copy.deepcopy(graph)
            changed["edges"].reverse()
            self.assertEqual(env.symbolic_count(changed),label)
    def test_protected_sources_not_callable(self):
        for lane,seed in (("Wingless",98200),("Yggdrasil",99200),("Wingless",96100)):
            with self.assertRaises(env.Invalid):
                env.build(seed,[1,1,2],lane)
    def test_privileged_field_dropped(self):
        p,_=env.build(98103,[1,1,2],"Wingless")
        p["true_route"]=[0]
        with self.assertRaises(env.Invalid):
            env.validate(p)
    def test_two_source_cohort(self):
        rows=env.train_rows("Wingless",[[1,1,2],[3,2,0]])
        self.assertEqual(len(rows),128)
        self.assertEqual(sum(y for _,y in rows),64)
        with self.assertRaises(env.Invalid):
            env.train_rows("Wingless",[[1,1,2],[1,1,2]])

if __name__=="__main__":
    unittest.main()
