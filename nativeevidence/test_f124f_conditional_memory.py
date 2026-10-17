"""F124-F source-only numeric gradient and bounded query retention qualification."""
import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124f_public_graph_source as graph
import f124f_conditional_memory as model

class QueryConditionedScientificTests(unittest.TestCase):
    def pair(self):
        return graph.build(160000,[1,1,2],"Wingless","TRAIN")

    def test_frozen_source_distinct_model_shape_and_training_budget(self):
        self.assertTrue(model.contract())
        self.assertEqual(model.EPOCHS,100)
        self.assertEqual(model.SLOTS,3)
        self.assertEqual((model.PA,model.PB),(19,20))
        self.assertEqual(model.initial("A"),model.initial("B")[:19])
        self.assertLessEqual(model.PB,128)

    def test_model_observes_only_public_fields_and_never_confirmation(self):
        pos,neg=self.pair()
        for arm in ("A","B"):
            for obs in (pos,neg):
                p,logit,grad,stats=model.forward(obs,model.initial(arm),arm)
                self.assertTrue(math.isfinite(p))
                self.assertTrue(math.isfinite(logit))
                self.assertIsNone(grad)
                self.assertLessEqual(stats["peak_key_records"],128)
                self.assertLessEqual(stats["max_messages_per_hop"],128)
                self.assertGreater(stats["raw_bit_multiply_adds"],0)
                self.assertEqual(stats["depth"],len(obs["roles"]))
        for k in ("truth","oracle_path","changed_token","precomputed_equal"):
            bad=copy.deepcopy(pos);bad[k]=1
            with self.subTest(k=k),self.assertRaises(graph.Invalid):
                model.forward(bad,model.initial("A"),"A")
        with self.assertRaises(graph.Invalid):
            graph.build(160100,[1,1,2],"Wingless","CONFIRM")
        with self.assertRaises(graph.Invalid):
            model.forward(pos,model.initial("B")[:-1],"B")

    def test_order_invariance_and_public_query_retention_ablation(self):
        pos,neg=self.pair()
        for arm in ("A","B"):
            weights=model.initial(arm)
            for obs in (pos,neg):
                swapped=copy.deepcopy(obs);swapped["edges"].reverse()
                yes=model.forward(obs,weights,arm)
                no=model.forward(swapped,weights,arm)
                self.assertAlmostEqual(yes[0],no[0],places=12)
                self.assertEqual(yes[3]["peak_key_records"],no[3]["peak_key_records"])
                baseline=model.forward(obs,weights,arm,query_priority=False)
                self.assertTrue(math.isfinite(baseline[0]))
                self.assertTrue(0<=baseline[0]<=1)
        self.assertEqual(graph.public_routes(pos),1)
        self.assertEqual(graph.public_routes(neg),0)

    def test_analytic_gradients_follow_admitted_selected_records(self):
        pos,_=self.pair()
        eps=1e-5
        for arm,indices in (("A",[0,1,7,15,16,17,18]),
                            ("B",[0,1,7,15,16,17,18,19])):
            w=model.initial(arm)
            base=model.forward(pos,w,arm)[0]
            _,_,grads,_=model.forward(pos,w,arm,base-1.)
            self.assertEqual(len(grads),len(w))
            self.assertTrue(all(math.isfinite(x) for x in grads))
            for k in indices:
                plus=list(w);minus=list(w)
                plus[k]+=eps;minus[k]-=eps
                hi=model.forward(pos,plus,arm)[0]
                lo=model.forward(pos,minus,arm)[0]
                num=(-math.log(hi)+math.log(lo))/(2*eps)
                self.assertAlmostEqual(grads[k],num,places=4)

    def test_reject_invalid_source_vectors(self):
        with self.assertRaises(graph.Invalid):
            model.train("Wingless",[[1,1,2],[1,1,2]],"A")
        with self.assertRaises(graph.Invalid):
            model.train("Yggdrasil",[[1,1,2]],"B")
        self.assertFalse(set(graph.TRAIN["Wingless"]) &
                         set(graph.RESERVED_CONFIRM["Wingless"]))

if __name__=="__main__":
    unittest.main()
