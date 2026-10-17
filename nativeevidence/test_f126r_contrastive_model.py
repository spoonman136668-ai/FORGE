"""F126-R no privileged prediction fields, fixed objective and causal audit."""
from pathlib import Path
import copy,math,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f126r_train_environment as env
import f126r_contrastive_model as m
class Contrastive(unittest.TestCase):
    def graphs(self):return env.build(160100,[1,2,3],"Wingless")
    def test_public_permutation_invariance_and_20_parameter_model(self):
        p,n=self.graphs()
        for g in (p,n):
            probability,d,receipt=m.forward(g,m.INIT,True)
            self.assertEqual(len(d),20)
            self.assertGreater(probability,0)
            self.assertLess(probability,1)
            self.assertLessEqual(receipt["work"]["state_peak"],256)
            self.assertLessEqual(receipt["work"]["candidate_expansions"],512)
            self.assertGreaterEqual(receipt["public_complete_paths"],6)
            self.assertFalse(receipt["protected_confirmation_read"])
            reverse=copy.deepcopy(g);reverse["edges"].reverse()
            self.assertAlmostEqual(m.forward(reverse,m.INIT)[0],probability,places=12)
    def test_no_oracle_access_and_no_paired_input(self):
        p,n=self.graphs()
        with patch.object(env,"graph_paths",side_effect=AssertionError("oracle")):
            m.forward(p,m.INIT)
        p["oracle_true_route"]=3
        with self.assertRaises(env.Invalid):m.forward(p,m.INIT)
    def test_fail_closed_model_and_confirmation(self):
        p,n=self.graphs()
        with self.assertRaises(env.Invalid):m.forward(p,[0.]*21)
        with self.assertRaises(env.Invalid):m.forward(p,[math.nan]*20)
        with self.assertRaises(env.Invalid):env.build(160200,[1,2,3],"Wingless")
    def test_label_blind_single_scramble_and_frozen_ablation(self):
        p,n=self.graphs()
        ref=m.null_graph(p)
        self.assertEqual(set(ref),set(p))
        self.assertEqual(ref["start"],p["start"])
        self.assertEqual(len(ref["edges"]),len(p["edges"]))
        self.assertEqual(m.null_graph(p),ref)
        self.assertNotEqual(ref,p)
        no_null=m.forward(p,m.INIT,ablation="NO_NULL")[0]
        self.assertTrue(0<no_null<1)
        self.assertEqual(len(m.forward(p,m.INIT,ablation="NO_NORMALIZATION")[1]),20)
if __name__=="__main__":unittest.main()
