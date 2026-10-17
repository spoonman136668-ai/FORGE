"""F124-R Sparse-2 public-input, parameter, and beam controls."""
from pathlib import Path
import copy,math,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124r_sparse_model as model
import f124r_train_environment as env

class Beam(unittest.TestCase):
    def graph(self):
        return env.build(98101,[1,1,2],"Wingless")
    def test_model_is_exactly_twenty_parameters(self):
        p,n=self.graph()
        self.assertEqual(len(model.init()),20)
        for graph in (p,n):
            result,gradient,trace=model.forward(graph,model.init(),trace=True)
            self.assertTrue(0<result<1)
            self.assertEqual(len(gradient),20)
            self.assertLessEqual(trace["work"]["retained_max"],2)
            self.assertEqual(trace["work"]["public_edge_visits"],len(graph["edges"]))
            self.assertGreater(trace["work"]["pruned_states"],0)
    def test_public_edge_order_invariance(self):
        for graph in self.graph():
            rev=copy.deepcopy(graph)
            rev["edges"].reverse()
            a=model.forward(graph,model.init(),trace=True)
            b=model.forward(rev,model.init(),trace=True)
            self.assertAlmostEqual(a[0],b[0],places=13)
            self.assertEqual(a[2],b[2])
    def test_symbolic_oracle_inaccessible_to_model(self):
        graph,_=self.graph()
        with patch.object(env,"symbolic_count",side_effect=AssertionError("oracle")):
            model.forward(graph,model.init())
        graph["oracle_true_path"]=0
        with self.assertRaises(env.Invalid):
            model.forward(graph,model.init())
    def test_missing_query_route_is_scored_not_removed(self):
        graph,_=self.graph()
        graph["target"]="not-reachable-query-node"
        p,grad,receipt=model.forward(graph,model.init(),trace=True)
        self.assertTrue(receipt["no_route_counted_as_failure"])
        self.assertAlmostEqual(p,model.sigmoid(model.init()[18]*(0-model.init()[19])))
    def test_parameter_validation(self):
        graph,_=self.graph()
        for weights in ([0.]*21,[math.nan]*20):
            with self.assertRaises(env.Invalid):
                model.forward(graph,weights)

if __name__=="__main__":
    unittest.main()
