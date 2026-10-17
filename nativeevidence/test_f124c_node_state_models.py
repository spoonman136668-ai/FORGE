"""F124-C TRAIN-only differentiable node-state mechanism qualification."""
import copy
import math
from pathlib import Path
import sys
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124c_reconvergent_graph as env
import f124c_node_state_models as m

VECTORS=[[1,1,2],[3,2,0]]

class LearnedNodeStateTests(unittest.TestCase):
    def pair(self):
        return env.build(100000,VECTORS[0],"Wingless","TRAIN")

    def test_frozen_arms_genuine_bounded_parameters(self):
        self.assertEqual(m.P_A,132)
        self.assertEqual(m.P_B,141)
        self.assertLessEqual(m.P_B,768)
        self.assertEqual(m.EPOCHS,100)
        self.assertEqual(m.initial("A"),m.initial("A"))
        self.assertNotEqual(len(m.initial("A")),len(m.initial("B")))
        self.assertGreater(len(set(m.initial("B")[:128])),32)

    def test_end_to_end_gradients_are_analytic_and_finite(self):
        pos,_=self.pair()
        for arm in ("A","B"):
            w=m.initial(arm)
            p,grads,stats=m.forward(pos,w,arm,1)
            self.assertTrue(math.isfinite(p))
            self.assertEqual(len(grads),len(w))
            self.assertTrue(all(math.isfinite(g) for g in grads))
            self.assertGreater(stats["gate_sigmoids"],0)
            self.assertLessEqual(stats["peak_state_slots"],128)
            for i in ([0,13,127,128,130] if arm=="A" else [0,13,127,128,130,132,139]):
                plus=list(w);minus=list(w);eps=1e-4
                plus[i]+=eps;minus[i]-=eps
                pp=m.forward(pos,plus,arm)[0]
                pm=m.forward(pos,minus,arm)[0]
                numeric=(-math.log(pp)+math.log(pm))/(2*eps)
                self.assertAlmostEqual(grads[i],numeric,places=5)

    def test_graph_permutation_invariance_both_arms(self):
        pos,neg=self.pair()
        for arm in ("A","B"):
            w=m.initial(arm)
            for obs in (pos,neg):
                reversed_graph=copy.deepcopy(obs)
                reversed_graph["edges"].reverse()
                p,_,s=m.forward(obs,w,arm)
                q,_,t=m.forward(reversed_graph,w,arm)
                self.assertAlmostEqual(p,q,places=12)
                self.assertEqual(s["peak_state_slots"],t["peak_state_slots"])
                self.assertEqual(s["max_incoming_messages"],t["max_incoming_messages"])

    def test_one_or_two_slots_and_no_path_or_oracle_arguments(self):
        pos,_=self.pair()
        a=m.forward(pos,m.initial("A"),"A")[2]
        b=m.forward(pos,m.initial("B"),"B")[2]
        self.assertGreater(b["peak_state_slots"],a["peak_state_slots"])
        self.assertGreater(b["prototype_sigmoids"],0)
        self.assertEqual(a["prototype_sigmoids"],0)
        self.assertGreater(b["slot_mass"][0],0)
        self.assertGreater(b["slot_mass"][1],0)
        for extra in ("selected_path","oracle","truth","changed_edge","same_value"):
            bad=copy.deepcopy(pos)
            bad[extra]=1
            with self.subTest(extra=extra),self.assertRaises(env.Quarantined):
                m.forward(bad,m.initial("B"),"B")
        with self.assertRaises(env.Quarantined):
            m.forward(pos,m.initial("B")[:-1],"B")

    def test_pair_changes_model_probabilities_without_label_leak(self):
        pos,neg=self.pair()
        for arm in ("A","B"):
            w=m.initial(arm)
            pp=m.forward(pos,w,arm)[0]
            pn=m.forward(neg,w,arm)[0]
            self.assertNotEqual(pp,pn)
            self.assertLess(abs(pp-pn),1.)

    def test_training_source_guards_no_confirmation(self):
        for bad in ("Wingless","Yggdrasil"):
            with self.subTest(lane=bad):
                with self.assertRaises(env.Quarantined):
                    m.train(bad,[[1,1,2],[1,1,2]],"A")
        with self.assertRaises(env.Quarantined):
            m.train_lanes({"Wingless":VECTORS})
        self.assertTrue(set(env.TRAIN["Wingless"]).isdisjoint(env.RESERVED_CONFIRM["Wingless"]))

if __name__=="__main__":
    unittest.main()
