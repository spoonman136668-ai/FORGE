"""F125-R public-token state preservation, exact merge and source guards."""
from pathlib import Path
import copy,math,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f125r_path_model as m
import f125r_train_environment as env

class Composer(unittest.TestCase):
    def graphs(self):return env.build(100100,[1,2,3],"Wingless")
    def test_all_public_hypotheses_and_no_k2(self):
        p,n=self.graphs()
        for graph in (p,n):
            v,d,t=m.forward(graph,list(m.INIT),True)
            self.assertTrue(0<v<1)
            self.assertEqual(len(d),20)
            self.assertEqual(t["hard_pruned_routes"],0)
            self.assertTrue(t["merged_only_identical_public_keys"])
            self.assertGreater(t["work"]["state_limit_peak"],2)
            self.assertLessEqual(t["work"]["state_limit_peak"],256)
            self.assertEqual(t["work"]["public_edge_visits"],len(graph["edges"]))
            self.assertGreater(t["work"]["edge_hash_bytes"],len(graph["edges"]))
    def test_canonical_graph_order_independent(self):
        for graph in self.graphs():
            reverse=copy.deepcopy(graph)
            reverse["edges"].reverse()
            a=m.forward(graph,list(m.INIT),True)
            b=m.forward(reverse,list(m.INIT),True)
            self.assertAlmostEqual(a[0],b[0],places=13)
            self.assertEqual(a[2],b[2])
    def test_no_symbolic_oracle_in_model(self):
        p,_=self.graphs()
        with patch.object(env,"graph_paths",side_effect=AssertionError("oracle")):
            m.forward(p,list(m.INIT),True)
        p["oracle_edge_index"]=0
        with self.assertRaises(env.Invalid):
            m.forward(p,list(m.INIT),True)
    def test_parameter_and_nonfinite_rejected(self):
        p,_=self.graphs()
        for w in ([0.]*21,[math.nan]*20):
            with self.assertRaises(env.Invalid):m.forward(p,w)
    def test_public_terminal_is_scored_when_unreachable(self):
        p,_=self.graphs()
        p["target"]="new-unreachable-public-target"
        value,_,r=m.forward(p,m.INIT,True)
        self.assertTrue(r["no_public_route"])
        self.assertAlmostEqual(value,m.sigmoid(m.INIT[-2]*(0-m.INIT[-1])))

if __name__=="__main__":unittest.main()
