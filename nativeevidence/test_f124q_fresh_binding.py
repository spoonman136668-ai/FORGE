"""F124-Q preregistered fresh source, real native model and no-oracle focused tests."""
import inspect
import math
import unittest

import f124q_fresh_source as source
import f124q_independent_binding as models
import f124q_training_evidence as evidence
import f124n_novel_structure_source as prior
import f124o_native_learners as original


class TestF124Q(unittest.TestCase):
    def test_preimplementation_identity_and_disjoint_seed_birth(self):
        p=evidence.validate_freeze()
        self.assertTrue(p["training"]["not_tune_after_DEV"])
        self.assertEqual(p["qualified_parent"]["sha"],
                         "497ef36d0a2d17c6ff474db97ba554a2f55536a4")
        self.assertEqual(source.git_blob(source.PROTOCOL.read_bytes().replace(
                         b"\r\n",b"\n")),source.PROTOCOL_BLOB)
        self.assertEqual(p["mechanisms"]["Wingless"]["trainable_parameters"],4)
        self.assertEqual(p["mechanisms"]["Yggdrasil"]["trainable_parameters"],2)
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(source.COHORTS[lane]["FIT"]).isdisjoint(
                            source.COHORTS[lane]["DEV"]))
            for phase in ("FIT","DEV"):
                self.assertTrue(set(source.COHORTS[lane][phase]).isdisjoint(
                                prior.COHORTS[lane]["FIT"]))
                self.assertTrue(set(source.COHORTS[lane][phase]).isdisjoint(
                                prior.COHORTS[lane]["DEV"]))
                self.assertTrue(set(source.COHORTS[lane][phase]).isdisjoint(
                                source.FORBIDDEN[lane]))
                self.assertEqual(len(source.COHORTS[lane][phase]),24)
        with self.assertRaises(source.Quarantined):
            source.protected()
        with self.assertRaises(source.Quarantined):
            source.build("Wingless",180100,[2,1,1],"DEV")

    def test_full_fresh_public_source_and_pair_integrity(self):
        for lane in ("Wingless","Yggdrasil"):
            for phase in ("FIT","DEV"):
                strata={7:0,8:0,9:0}
                for vector in source.VECTORS:
                    for seed in source.COHORTS[lane][phase]:
                        pos,neg=source.build(lane,seed,vector,phase)
                        self.assertTrue(source.paired_admit(pos,neg))
                        strata[len(pos["roles"])]+=1
                self.assertEqual(strata,{7:16,8:16,9:16})

    def test_anchored_wingless_and_fixed_yggdrasil_cells(self):
        base_w=list(original.WINGLESS_INIT)
        anchored=models.wingless_anchored_weights(base_w,[0.,0.,0.,0.])
        self.assertEqual(anchored[:4],[1.,1.,1.,1.])
        self.assertEqual(anchored[4:],base_w[4:])
        mod=models.wingless_anchored_weights(base_w,[1.,0.,0.,0.])
        self.assertTrue(all(.8 <= v <= 1.2 for v in mod[:4]))
        self.assertNotEqual(mod[:4],anchored[:4])
        ygg=list(original.YGGDRASIL_INIT)
        for lane,seed in (("Wingless",480000),("Yggdrasil",490000)):
            pos,neg=source.build(lane,seed,[2,1,1],"FIT")
            for graph in (pos,neg):
                if lane=="Wingless":
                    w=model_w=base_w
                    result,stats=models.forward(lane,graph,w,[0,0,0,0])
                    self.assertEqual(stats["state_limit"],3)
                    self.assertLessEqual(stats["max_active"],192)
                else:
                    old,_=original.forward(lane,graph,ygg)
                    result,stats=models.forward(lane,graph,ygg,[0,0])
                    self.assertAlmostEqual(old,result,places=10)
                    self.assertEqual(stats["active_cell_limit"],7)
                    self.assertEqual(stats["retained_cell_limit"],9)
                    self.assertLessEqual(stats["max_active"],7)
                    self.assertLessEqual(stats["max_retained"],9)
                self.assertTrue(math.isfinite(result))
                self.assertGreater(stats["public_edge_scans"],0)

    def test_label_blind_and_fit_only_optimizer(self):
        fn=inspect.getsource(models.forward)+inspect.getsource(
            models.yggdrasil_lookahead)+inspect.getsource(
            models.wingless_anchored_weights)
        for forbidden in ("public_routes(","symbolic_routes(","protected(",
                          "true_path","truth_label"):
            self.assertNotIn(forbidden,fn)
        train_source=inspect.getsource(models.train)+inspect.getsource(models.fit_pairs)
        self.assertNotIn('["DEV"]',train_source)
        self.assertNotIn('"DEV"',train_source)
        with self.assertRaises((source.Quarantined,prior.Quarantined)):
            models.forward("Wingless",{"oracle":True},
                           list(original.WINGLESS_INIT),[0,0,0,0])


if __name__=="__main__":
    unittest.main()
