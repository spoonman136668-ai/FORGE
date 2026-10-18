"""F124-R exact source/preimplementation and bounded two-lane learnability."""
import inspect
import math
import unittest

import f124r_fresh_source as source
import f124r_causal_learners as learner
import f124r_training_evidence as evidence
import f124o_native_learners as original
import f124q_fresh_source as old_source


class F124RTests(unittest.TestCase):
    def test_freeze_commit_and_original_code_immutable(self):
        p=evidence.authentic_freeze()
        self.assertEqual(source.PROTOCOL_BLOB,
                         "a4db651492631ad1be141ab2a0a6e1c86dad60ea")
        self.assertEqual(p["parent"]["commit_sha"],
                         "a3ef79b3dc10dcc4d544f808e35897e72ed4a154")
        self.assertTrue(p["fresh_public_source"]["not_independent_original_firstuse"])
        self.assertTrue(p["optimizer"]["no_post_DEV_parameter_modification"])
        self.assertEqual(p["models"]["Wingless"]["trainable_coefficients"],2)
        self.assertEqual(p["models"]["Yggdrasil"]["trainable_coefficients"],2)
        self.assertEqual(evidence.blob(original),evidence.BASE_BLOB)
        self.assertEqual(evidence.blob(evidence.previous_q),evidence.Q_BLOB)

    def test_new_public_SOURCE_identity_and_complete_denominator(self):
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(source.COHORTS[lane]["FIT"]).isdisjoint(
                            source.COHORTS[lane]["DEV"]))
            self.assertTrue(set(source.COHORTS[lane]["FIT"]).isdisjoint(
                            old_source.COHORTS[lane]["FIT"]))
            self.assertTrue(set(source.COHORTS[lane]["DEV"]).isdisjoint(
                            old_source.COHORTS[lane]["DEV"]))
            for phase in ("FIT","DEV"):
                depths={7:0,8:0,9:0}
                for vector in source.VECTORS:
                    for seed in source.COHORTS[lane][phase]:
                        pos,neg=source.build(lane,seed,vector,phase)
                        self.assertTrue(source.paired_admit(pos,neg))
                        depths[len(pos["roles"])]+=1
                self.assertEqual(depths,{7:16,8:16,9:16})
        with self.assertRaises(source.Quarantined):
            source.build("Wingless",180100,source.VECTORS[0],"DEV")
        with self.assertRaises(source.Quarantined):
            source.protected()

    def test_yggdrasil_continuous_evidence_no_cell_capacity_growth(self):
        lane="Yggdrasil";base=list(original.YGGDRASIL_INIT)
        positive,negative=source.build(lane,590000,[2,1,1],"FIT")
        for graph in (positive,negative):
            prior,_=original.yggdrasil_forward(graph,base)
            zero,work=learner.yggdrasil_continuous(graph,base,[0.,0.])
            self.assertAlmostEqual(prior,zero,places=12)
            self.assertEqual(work["active_cell_limit"],7)
            self.assertEqual(work["retained_cell_limit"],9)
            self.assertLessEqual(work["max_active"],7)
            self.assertLessEqual(work["max_retained"],9)
            changed,_=learner.yggdrasil_continuous(graph,base,[.4,.2])
            self.assertTrue(math.isfinite(changed))
            self.assertGreater(work["public_edge_scans"],0)

    def test_wingless_true_raw_key_calibration_not_merely_channel_weight(self):
        positive,negative=source.build("Wingless",580000,[2,1,1],"FIT")
        for graph in (positive,negative):
            a,work=learner.wingless_calibrated(
                graph,list(original.WINGLESS_INIT),[0.,0.])
            b,_=learner.wingless_calibrated(
                graph,list(original.WINGLESS_INIT),[.4,0.])
            self.assertTrue(math.isfinite(a) and math.isfinite(b))
            self.assertEqual(work["state_limit"],3)
            self.assertLessEqual(work["max_active"],192)
            self.assertGreater(work["causal_key_comparisons"],0)
            self.assertGreater(work["raw_bit_ops"],0)

    def test_readout_is_label_blind_and_train_never_constructs_DEV(self):
        source_code=inspect.getsource(learner.wingless_calibrated)+inspect.getsource(
            learner.yggdrasil_continuous)
        for forbidden in ("public_routes(", "protected(", "oracle_truth",
                          "symbolic_routes(", "true_path"):
            self.assertNotIn(forbidden,source_code)
        train_src=inspect.getsource(learner.train)+inspect.getsource(learner.fit_pairs)
        self.assertNotIn('"DEV"',train_src)
        self.assertNotIn('["DEV"]',train_src)
        with self.assertRaises(ValueError):
            learner.forward("Yggdrasil",{"oracle_label":True},
                            list(original.YGGDRASIL_INIT),[0.,0.])


if __name__=="__main__":
    unittest.main()
