"""F126-R never accesses protected cohorts; two source-authenticated TRAIN lanes."""
from pathlib import Path
import copy
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f126r_train_environment as env

class Source(unittest.TestCase):
    def test_new_family_complete_paired_cases(self):
        for lane,seed in (("Wingless",160100),("Wingless",160101),
                          ("Yggdrasil",170100),("Yggdrasil",170101)):
            with self.subTest(lane=lane,seed=seed):
                positive,negative=env.build(seed,[1,2,3],lane)
                self.assertEqual(set(positive),env.FIELDS)
                self.assertEqual(env.marginals(positive),env.marginals(negative))
                self.assertEqual(env.graph_paths(positive,True),1)
                self.assertEqual(env.graph_paths(negative,True),0)
                self.assertEqual(env.graph_paths(positive),env.graph_paths(negative))
                self.assertIn(env.graph_paths(positive),range(6,13))
                self.assertEqual(env.build(seed,[1,2,3],lane),(positive,negative))
    def test_fail_closed_reserved_and_parent_seeds(self):
        for lane,seed in (("Wingless",160200),("Yggdrasil",170200),
                          ("Wingless",100100),("Yggdrasil",101100)):
            with self.assertRaises(env.Invalid):
                env.build(seed,[1,2,3],lane)
    def test_input_edge_permutation_and_privileged_fields(self):
        positive,negative=env.build(160102,[2,1,0],"Wingless")
        for graph,label in ((positive,1),(negative,0)):
            reordered=copy.deepcopy(graph);reordered["edges"].reverse()
            self.assertEqual(env.graph_paths(reordered,True),label)
            graph["oracle_index"]=0
            with self.assertRaises(env.Invalid):env.validate(graph)
    def test_full_train_denominator_and_source_distinction(self):
        rows=env.train_rows("Wingless",[[1,2,3],[2,3,1]])
        self.assertEqual(len(rows),128)
        self.assertEqual(sum(y for _,y in rows),64)
        with self.assertRaises(env.Invalid):
            env.train_rows("Wingless",[[1,2,3],[1,2,3]])

if __name__=="__main__":
    unittest.main()
