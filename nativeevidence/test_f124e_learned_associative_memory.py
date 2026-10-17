"""F124-E bounded differentiable key-value memory, TRAIN-only tests."""
import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124e_key_value_environment as source
import f124e_learned_associative_memory as net

class F124EAssociativeQualification(unittest.TestCase):
    def graphs(self):
        return source.build(140000,[1,1,2],"Wingless","TRAIN")

    def test_distinct_three_slot_learned_mechanisms(self):
        self.assertTrue(net.contract())
        self.assertEqual(net.SLOTS,3)
        self.assertEqual(net.EPOCHS,100)
        self.assertEqual((net.PARAM_A,net.PARAM_B),(132,156))
        self.assertTrue(net.PARAM_B<=768)
        self.assertEqual(net.initial("A"),net.initial("B")[:net.PARAM_A])

    def test_key_value_records_are_bounded_and_have_work_counts(self):
        pos,neg=self.graphs()
        for arm in ("A","B"):
            w=net.initial(arm)
            for graph in (pos,neg):
                p,logit,gradient,cost=net.forward(graph,w,arm)
                self.assertTrue(math.isfinite(p))
                self.assertTrue(math.isfinite(logit))
                self.assertIsNone(gradient)
                self.assertLessEqual(cost["peak_key_value_records"],128)
                self.assertGreater(cost["terminal_record_count"],0)
                self.assertGreater(cost["public_edge_scans"],0)
                self.assertGreater(cost["latent_multiply_adds"],0)
                self.assertGreater(cost["raw_bit_multiply_adds"],0)

    def test_edge_order_invariance(self):
        p,n=self.graphs()
        for arm in ("A","B"):
            w=net.initial(arm)
            for graph in (p,n):
                flipped=copy.deepcopy(graph)
                flipped["edges"].reverse()
                a=net.forward(graph,w,arm)
                b=net.forward(flipped,w,arm)
                self.assertAlmostEqual(a[0],b[0],places=12)
                self.assertEqual(a[3]["peak_key_value_records"],
                                 b[3]["peak_key_value_records"])

    def test_end_to_end_analytic_gradients_include_b_prototypes(self):
        pos,_=self.graphs()
        h=2e-5
        for arm,idxs in (("A",[0,17,126,128,129,130,131]),
                         ("B",[0,17,126,128,129,130,131,132,140,148])):
            weights=net.initial(arm)
            prob,_,grad,counts=net.forward(
                pos,weights,arm,net.forward(pos,weights,arm)[0]-1.)
            self.assertEqual(len(grad),len(weights))
            self.assertTrue(all(math.isfinite(x) for x in grad))
            if arm=="B":
                self.assertGreater(max(abs(x) for x in grad[132:]),1e-11)
            for k in idxs:
                left,right=list(weights),list(weights)
                left[k]+=h;right[k]-=h
                lp=net.forward(pos,left,arm)[0]
                rp=net.forward(pos,right,arm)[0]
                numeric=(-math.log(lp)+math.log(rp))/(2*h)
                self.assertAlmostEqual(grad[k],numeric,places=4)

    def test_counterfactuals_and_privileged_features(self):
        pos,neg=self.graphs()
        self.assertEqual(source.public_routes(pos),1)
        self.assertEqual(source.public_routes(neg),0)
        for arm in ("A","B"):
            weights=net.initial(arm)
            a=net.forward(pos,weights,arm)[0]
            b=net.forward(neg,weights,arm)[0]
            self.assertNotEqual(a,b)
        for marker in ("oracle_path","same_bits","selected_edge","truth","seed"):
            altered=copy.deepcopy(pos);altered[marker]=1
            with self.assertRaises(source.Invalid):
                net.forward(altered,net.initial("A"),"A")
        with self.assertRaises(source.Invalid):
            net.forward(pos,net.initial("B")[:-1],"B")

    def test_frozen_vectors_and_holdout_rejected(self):
        with self.assertRaises(source.Invalid):
            net.train("Wingless",[[1,1,2],[1,1,2]],"A")
        with self.assertRaises(source.Invalid):
            net.train("Wingless",[[1,1,2]],"A")
        with self.assertRaises(source.Invalid):
            source.build(140100,[1,1,2],"Wingless","CONFIRM")
        self.assertFalse(set(source.TRAIN["Yggdrasil"]) &
                         set(source.RESERVED_CONFIRM["Yggdrasil"]))

if __name__=="__main__":
    unittest.main()
