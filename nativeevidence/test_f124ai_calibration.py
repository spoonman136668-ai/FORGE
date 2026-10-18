"""F124-AI preregistration, hand-coded identity attribution, FIT-only calibration tests."""
import json,unittest
import f124ai_source as S
import f124ai_calibration as C
import f124ad_intermediate_credit as AD
import f124o_native_learners as O

class F124AIFocused(unittest.TestCase):
    def test_source_preimplementation_identity_and_protected_quarantine(self):
        self.assertEqual(len(S.frozen()),64)
        x=json.loads(S.PROTOCOL.read_text())
        self.assertEqual(x["parent"]["exact_head"],
                         "5f020bed602abd59400fc7c87a17216e2049ed07")
        self.assertEqual(x["parent"]["actions"],39112820003)
        self.assertEqual(x["hypotheses"]["parameter_count"]["global_learned_total"],3)
        self.assertTrue(all(not b for b in x["guardrails"].values()))
        with self.assertRaises(S.Quarantined):S.protected()

    def test_fresh_noisy_FIT_DEV_source_admission(self):
        self.assertEqual(len(set(C.CODES)),16)
        self.assertTrue(all(float.hex(v) for v in C.CODES))
        self.assertEqual(C.CODES,tuple(10.+j/8. for j in range(16)))
        for family in S.FAMILIES:
            self.assertTrue(set(S.COHORTS[family]["FIT"]).isdisjoint(
                            S.COHORTS[family]["DEV"]))
            for phase in ("FIT","DEV"):
                by_depth={10:0,11:0,12:0}
                for v in S.VECTORS:
                    for seed in S.COHORTS[family][phase]:
                        pos,neg=S.build(family,seed,v,phase)
                        self.assertTrue(S.paired_admit(pos,neg))
                        by_depth[len(pos["roles"])]+=1
                self.assertEqual(by_depth,{10:16,11:16,12:16})

    def test_handcoded_index_not_learned_and_original_16_cells(self):
        self.assertIs(C.original_learner().__code__,AD.forward.__code__)
        weights={"base":list(O.YGGDRASIL_INIT),
                 "R":[.03,-.01],"S":[.02,.06],"U":[.03,-.05]}
        cal={"slope":2.,"bias":1.}
        for fam in S.FAMILIES:
            pos,neg=S.build(fam,3090000,[2,1,1],"FIT")
            for g in (pos,neg):
                fixed=C.fingerprint_infer(g,"fixed",cal,.5)
                trained=C.fingerprint_infer(g,"trained",cal,.5)
                self.assertFalse(fixed["blocked"])
                self.assertFalse(trained["blocked"])
                self.assertLessEqual(fixed["actual_cell_peak"],16)
                self.assertLessEqual(trained["actual_cell_peak"],16)
                self.assertGreater(fixed["edge_scans"],0)
                for who in ("O","U"):
                    old=C.original_learner()(who,g,weights)
                    self.assertLessEqual(old["final_active"],7)
                    self.assertLessEqual(old["final_retained"],9)
            self.assertTrue(C.fingerprint_infer(pos,"fixed",cal,.5)["prediction"])
            self.assertFalse(C.fingerprint_infer(neg,"fixed",cal,.5)["prediction"])

    def test_true_FIT_supervision_and_frozen_thresholds(self):
        self.assertEqual(len(C.training_samples()),288)
        self.assertEqual(C.EPOCHS,100)
        self.assertEqual(C.LR,.05)
        self.assertEqual(C.THRESHOLDS,
            (.01,.05,.1,.2,.3,.4,.5,.6,.7,.8,.9,.95,.99))
        self.assertIn("trained_collisionfree_calibrator",C.ARMS)
        self.assertIn("fixed_collisionfree_index",C.ARMS)
        self.assertEqual(C.logistic(0.),.5)

if __name__=="__main__":unittest.main()
