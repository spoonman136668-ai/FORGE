"""F124-P frozen source/architecture and source-independent regression checks."""
import unittest

import f124o_native_learners as original
import f124n_novel_structure_source as source_n
import f124k_extended_source as source_k
import f124p_frozen_variants as variants
import f124p_ablation_receipt as receipt


class TestF124PFrozenAblations(unittest.TestCase):
    def test_protocol_source_identity_and_complete_gates(self):
        p=receipt.read_freeze()
        self.assertEqual(p["study"]["additional_training_steps"],0)
        self.assertEqual(p["source_parent"]["qualified_f124o_actions_run"],39078269441)
        self.assertEqual(p["study"]["criteria"]["full_pair_count_per_lane_per_source"],48)
        self.assertTrue(p["study"]["criteria"]["NO_PROTECTED_ACCEPTANCE"])
        self.assertEqual(len(p["study"]["comparison_arms"]["Wingless"]),7)
        self.assertEqual(len(p["study"]["comparison_arms"]["Yggdrasil"]),7)

    def test_frozen_original_replay_identity_and_memory_cap(self):
        for lane,seed in (("Wingless",380000),("Yggdrasil",390000)):
            pos,neg=source_n.build(lane,seed,source_n.VECTORS[0],"FIT")
            w=list(original.WINGLESS_INIT if lane=="Wingless"
                   else original.YGGDRASIL_INIT)
            for graph in (pos,neg):
                before,cost=original.forward(lane,graph,w)
                exact,_=variants.variant_forward(lane,"original",graph,w)
                self.assertAlmostEqual(before,exact,places=12)
                for arm in ("ablate_compression","ablate_secondary","candidate"):
                    got,stats=variants.variant_forward(lane,arm,graph,w)
                    self.assertTrue(abs(got)<1000)
                    self.assertGreaterEqual(stats["public_edge_scans"],0)
                    if lane=="Wingless":
                        self.assertLessEqual(stats["max_active"],192)
                    else:
                        self.assertLessEqual(stats["max_active"],7)
                        self.assertLessEqual(stats["max_retained"],9)
                if lane=="Yggdrasil":
                    clone,_=variants.yggdrasil_cell_variant(graph,w)
                    self.assertAlmostEqual(before,clone,places=12)

    def test_k_source_and_protected_denial(self):
        for lane in ("Wingless","Yggdrasil"):
            seed=next(iter(source_k.FIXTURES[lane]))
            p,n=source_k.build_fixture(seed,[1,1,2],lane,"QUALIFICATION_FIXTURE")
            self.assertTrue(source_k.paired_admit(p,n))
            self.assertEqual(source_k.symbolic_routes(p),1)
            self.assertEqual(source_k.symbolic_routes(n),0)
            w=list(original.WINGLESS_INIT if lane=="Wingless"
                   else original.YGGDRASIL_INIT)
            for arm in ("original","candidate"):
                _,work=variants.variant_forward(lane,arm,p,w)
                self.assertGreater(work["public_edge_scans"],0)
            with self.assertRaises(source_k.Invalid):
                source_k.build_protected(seed=180100)
        with self.assertRaises(source_n.Quarantined):
            variants.variant_forward("Wingless","candidate",
                                     {"oracle_label":True},
                                     list(original.WINGLESS_INIT))


if __name__=="__main__":
    unittest.main()
