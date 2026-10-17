"""F124-D genuine learned competition: gradients, conservation, anti-splicing.

All samples are frozen TRAIN; no reserved CONFIRM call.
"""
import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124d_reconvergent_source as source
import f124d_competitive_states as network

class F124DModelQualification(unittest.TestCase):
    def graph(self):
        return source.build(120000,[1,1,2],"Wingless","TRAIN")

    def test_independent_frozen_source_and_parameter_limits(self):
        self.assertTrue(network.contract())
        self.assertEqual((network.P_A,network.P_B),(148,149))
        self.assertEqual(network.EPOCHS,100)
        self.assertLessEqual(network.P_B,768)
        self.assertEqual(network.initialize("A"),network.initialize("A"))
        self.assertEqual(network.initialize("A")[:148],
                         network.initialize("B")[:148])

    def test_mass_conserved_and_two_slots_not_enumerated_paths(self):
        positive,negative=self.graph()
        for arm in ("A","B"):
            for graph in (positive,negative):
                p,logit,grad,stats=network.forward(
                    graph,network.initialize(arm),arm)
                self.assertTrue(math.isfinite(p))
                self.assertTrue(math.isfinite(logit))
                self.assertIsNone(grad)
                self.assertLess(stats["max_mass_conservation_excess"],1e-9)
                self.assertLessEqual(stats["peak_state_slots"],128)
                self.assertLessEqual(stats["max_live_messages"],128)
                self.assertGreater(stats["exp_evaluations"],0)
                self.assertGreater(stats["raw_bit_mult_adds"],0)
                self.assertEqual(len(stats["last_slot_masses"]),2)
                self.assertEqual(len(stats["per_hop_total_mass"]),len(graph["roles"]))
                previous=1.
                for current in stats["per_hop_total_mass"]:
                    self.assertLessEqual(current,previous+1e-9)
                    previous=current

    def test_adjacency_order_does_not_change_prediction(self):
        positive,negative=self.graph()
        for arm in ("A","B"):
            w=network.initialize(arm)
            for g in (positive,negative):
                reversed_graph=copy.deepcopy(g)
                reversed_graph["edges"].reverse()
                pp=network.forward(g,w,arm)
                pn=network.forward(reversed_graph,w,arm)
                self.assertAlmostEqual(pp[0],pn[0],places=12)
                self.assertEqual(pp[3]["peak_state_slots"],
                                 pn[3]["peak_state_slots"])

    def test_raw_public_graph_no_privileged_markers(self):
        p,_=self.graph()
        for marker in ("correct_route","equality","seed","oracle_path","changed_edge"):
            corrupt=copy.deepcopy(p)
            corrupt[marker]=True
            with self.subTest(marker=marker),self.assertRaises(source.Invalid):
                network.forward(corrupt,network.initialize("B"),"B")
        with self.assertRaises(source.Invalid):
            network.forward(p,network.initialize("B")[:-1],"B")
        with self.assertRaises(source.Invalid):
            source.build(120100,[1,1,2],"Wingless","CONFIRM")

    def test_analytic_gradient_for_raw_bits_attention_and_slot_prototypes(self):
        p,_=self.graph()
        h=1e-5
        for arm,indices in (("A",[0,8,127,128,130,132,139,147]),
                            ("B",[0,8,127,128,130,132,139,147,148])):
            w=network.initialize(arm)
            pr,_,_,_=network.forward(p,w,arm)
            prob,logit,grad,stats=network.forward(p,w,arm,pr-1.)
            self.assertEqual(len(grad),len(w))
            self.assertTrue(all(math.isfinite(g) for g in grad))
            for k in indices:
                left,right=list(w),list(w)
                left[k]+=h;right[k]-=h
                plus=network.forward(p,left,arm)[0]
                minus=network.forward(p,right,arm)[0]
                numeric=(-math.log(plus)+math.log(minus))/(2.*h)
                self.assertAlmostEqual(grad[k],numeric,places=5)

    def test_counterfactuals_have_different_raw_gated_predictions(self):
        positive,negative=self.graph()
        for arm in ("A","B"):
            w=network.initialize(arm)
            pp=network.forward(positive,w,arm)[0]
            pn=network.forward(negative,w,arm)[0]
            self.assertGreater(abs(pp-pn),1e-10)
            self.assertEqual(source.routes(positive),1)
            self.assertEqual(source.routes(negative),0)

    def test_train_entry_requires_two_frozen_vector_sources(self):
        with self.assertRaises(source.Invalid):
            network.train("Wingless",[[1,1,2],[1,1,2]],"A")
        with self.assertRaises(source.Invalid):
            network.train("Yggdrasil",[[1,1,2]],"B")
        self.assertTrue(set(source.TRAIN["Yggdrasil"]).isdisjoint(
                        set(source.RESERVED_CONFIRM["Yggdrasil"])))

if __name__=="__main__":
    unittest.main()
