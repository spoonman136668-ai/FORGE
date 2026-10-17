"""F124-H trainable signed-depth and competing-evidence TRAIN-only tests."""
import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124h_source as src
import f124h_signed_evidence as m

class FrozenDepthEvidence(unittest.TestCase):
    def pair(self):
        return src.build(180000,[1,1,2],"Wingless","TRAIN")

    def test_exact_freeze_and_independent_sources(self):
        self.assertEqual(src.FREEZE_BLOB,"5b3ca556f2cf55323b6317d506a62c6b2a4aab85")
        self.assertEqual(len(src.frozen()),64)
        self.assertTrue(m.frozen())
        self.assertEqual(m.EPOCHS,100)
        self.assertEqual((m.PARAM_A,m.PARAM_B),(20,21))
        self.assertEqual(m.SLOTS,3)
        self.assertEqual(m.initial("A"),m.initial("B")[:20])

    def test_both_models_are_finite_public_bounded_and_depth_normalized(self):
        pos,neg=self.pair()
        for arm in ("A","B"):
            for g in (pos,neg):
                p,logit,grads,work=m.forward(g,m.initial(arm),arm)
                self.assertTrue(0<=p<=1)
                self.assertTrue(math.isfinite(logit))
                self.assertIsNone(grads)
                self.assertLessEqual(work["peak_key_records"],128)
                self.assertLessEqual(work["max_messages_per_hop"],128)
                self.assertEqual(work["depth"],len(g["roles"]))
                self.assertGreater(work["raw_bit_multiply_adds"],0)
                self.assertGreater(work["readout_compared_hops"],0)
                self.assertTrue(math.isfinite(work["terminal_mean_signed_evidence"]))

    def test_edges_unordered_and_models_differ_as_mechanisms(self):
        pos,neg=self.pair()
        for arm in ("A","B"):
            weights=m.initial(arm)
            for g in (pos,neg):
                reverse=copy.deepcopy(g);reverse["edges"].reverse()
                p=m.forward(g,weights,arm)
                q=m.forward(reverse,weights,arm)
                self.assertAlmostEqual(p[0],q[0],places=12)
                self.assertEqual(p[3]["peak_key_records"],q[3]["peak_key_records"])
        self.assertEqual(src.public_routes(pos),1)
        self.assertEqual(src.public_routes(neg),0)

    def test_genuine_analytic_selected_route_gradients(self):
        pos,_=self.pair()
        eps=1e-5
        for arm,ids in (("A",[0,2,7,16,17,18,19]),
                        ("B",[0,2,7,16,17,18,19,20])):
            weights=m.initial(arm)
            probability=m.forward(pos,weights,arm)[0]
            _,_,grads,_=m.forward(pos,weights,arm,probability-1.)
            self.assertEqual(len(grads),len(weights))
            self.assertTrue(all(math.isfinite(g) for g in grads))
            for k in ids:
                plus=list(weights);minus=list(weights)
                plus[k]+=eps;minus[k]-=eps
                high=m.forward(pos,plus,arm)[0]
                low=m.forward(pos,minus,arm)[0]
                num=(-math.log(high)+math.log(low))/(2*eps)
                self.assertAlmostEqual(grads[k],num,places=4)

    def test_privilege_and_holdout_rejected(self):
        pos,_=self.pair()
        for k in ("truth","selected_path","engineered_equality","source_seed"):
            g=copy.deepcopy(pos);g[k]=1
            with self.subTest(k=k),self.assertRaises(src.Invalid):
                m.forward(g,m.initial("A"),"A")
        with self.assertRaises(src.Invalid):
            m.forward(pos,m.initial("B")[:-1],"B")
        with self.assertRaises(src.Invalid):
            src.build(180100,[1,1,2],"Wingless","CONFIRM")
        with self.assertRaises(src.Invalid):
            m.train("Wingless",[[1,1,2],[1,1,2]],"A")
        self.assertFalse(set(src.TRAIN["Yggdrasil"]) & set(src.RESERVED_CONFIRM["Yggdrasil"]))

if __name__=="__main__":
    unittest.main()
