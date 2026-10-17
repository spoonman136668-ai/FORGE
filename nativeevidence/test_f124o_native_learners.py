"""F124-O bounded dual native model and qualification tests."""
import inspect
import json
import unittest

import f124n_novel_structure_source as source
import f124o_native_learners as m
import f124o_training_evidence as e


class F124OTests(unittest.TestCase):
    def test_source_frozen_before_code_and_distinct_architectures(self):
        p=e.read_freeze()
        self.assertEqual(p["arms"]["Wingless"]["slots_per_node"],3)
        self.assertEqual(p["arms"]["Yggdrasil"]["active_cells"],7)
        self.assertEqual(p["arms"]["Yggdrasil"]["retained_cells"],9)
        self.assertNotEqual(p["arms"]["Wingless"]["name"],
                            p["arms"]["Yggdrasil"]["name"])
        self.assertNotEqual(m.sha(m.WINGLESS_INIT),m.sha(m.YGGDRASIL_INIT))
        self.assertTrue(p["optimizer"]["fit_only_training"])
        self.assertTrue(p["optimizer"]["no_dev_gradient_or_selection"])
        self.assertFalse(p["evaluation"]["dev_success_not_assumed"])

    def test_same_public_graph_different_model_with_reordering(self):
        for lane,seed in (("Wingless",380000),("Yggdrasil",390000)):
            pos,neg=source.build(lane,seed,source.VECTORS[0],"FIT")
            initial=list(m.WINGLESS_INIT if lane=="Wingless" else m.YGGDRASIL_INIT)
            a,work=m.forward(lane,pos,initial)
            b,other=m.forward(lane,neg,initial)
            self.assertTrue(abs(a)<100 and abs(b)<100)
            shuffled=dict(pos)
            shuffled["edges"]=list(reversed(pos["edges"]))
            rev,_=m.forward(lane,shuffled,initial)
            self.assertAlmostEqual(a,rev,places=10)
            if lane=="Wingless":
                self.assertEqual(work["state_limit"],3)
                self.assertLessEqual(work["max_active"],192)
            else:
                self.assertEqual(work["active_cell_limit"],7)
                self.assertEqual(work["retained_cell_limit"],9)
                self.assertLessEqual(work["max_active"],7)
                self.assertLessEqual(work["max_retained"],9)
            self.assertGreater(work["public_edge_scans"],0)
            self.assertGreater(other["raw_bit_ops"],0)

    def test_no_oracle_or_reserved_model_interfaces(self):
        a=inspect.getsource(m.wingless_forward)
        b=inspect.getsource(m.yggdrasil_forward)
        for function in (a,b):
            self.assertNotIn("public_routes(",function)
            self.assertNotIn("protected(",function)
            self.assertNotIn("RESERVED",function)
        with self.assertRaises(source.Quarantined):
            m.forward("Wingless",{"oracle_truth":True},list(m.WINGLESS_INIT))
        with self.assertRaises(source.Quarantined):
            source.build("Wingless",180100,source.VECTORS[0],"DEV")
        with self.assertRaises(source.Quarantined):
            source.protected()


if __name__=="__main__":
    unittest.main()
