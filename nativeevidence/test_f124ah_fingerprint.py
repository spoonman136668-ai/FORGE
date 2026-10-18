"""F124-AH frozen independent FIT-only training, 16-cell inference and noisy semantics."""
import json,unittest
import f124ah_source as S
import f124ah_learned_fingerprint as L
import f124ah_comparison as C
import f124ad_intermediate_credit as AD
import f124ag_noisy_controls as AG
import f124o_native_learners as O

class FrozenRelationshipFingerprint(unittest.TestCase):
    def test_immutable_source_and_scientific_boundary(self):
        self.assertEqual(len(S.frozen()),64)
        p=json.loads(S.PROTOCOL.read_text())
        self.assertEqual(p["qualified_parent"]["head"],
                         "dad429047450b2b0dffbf61722d9fb9cef106e07")
        self.assertEqual(p["qualified_parent"]["actions"],39111665880)
        self.assertEqual(p["models"]["sgd"]["epochs"],100)
        self.assertEqual(p["models"]["train_and_eval_budget"]["max_total"],16)
        self.assertEqual(tuple(p["models"]["models"]
                          if "models" in p["models"] else
                          p["models"]["historical_original"]),
                         ("O_original","O_combined","U_original","U_combined"))
        self.assertTrue(all(v is False for v in p["governance"].values()))
        with self.assertRaises(S.Quarantined):S.protected()

    def test_new_FIT_DEV_positive_negative_distinct_and_stratified(self):
        for fam in S.FAMILIES:
            self.assertTrue(set(S.COHORTS[fam]["FIT"]).isdisjoint(
                            S.COHORTS[fam]["DEV"]))
            for phase in ("FIT","DEV"):
                strata={10:0,11:0,12:0}
                for v in S.VECTORS:
                    for seed in S.COHORTS[fam][phase]:
                        pos,neg=S.build(fam,seed,v,phase)
                        self.assertTrue(S.paired_admit(pos,neg))
                        strata[len(pos["roles"])]+=1
                self.assertEqual(strata,{10:16,11:16,12:16})

    def test_original_historical_bytecode_fixed_source_and_16_cells(self):
        fn=C.historical()
        self.assertIs(fn.__code__,AD.forward.__code__)
        w={"base":list(O.YGGDRASIL_INIT),"R":[.01,.02],
           "S":[.04,-.02],"U":[.04,.08]}
        codes=L.init_codebook()
        self.assertEqual(len(codes),16)
        for fam in S.FAMILIES:
            pos,neg=S.build(fam,2990000,[2,1,1],"FIT")
            for g in (pos,neg):
                for arm in ("O","U"):
                    for coeff in ({},{"gamma":.1,"penalty":1.}):
                        m=fn(arm,g,w,**coeff)
                        self.assertLessEqual(m["final_active"],7)
                        self.assertLessEqual(m["final_retained"],9)
                for threshold in (0.0001,0.49):
                    pred=L.inference(g,codes,threshold)
                    self.assertLessEqual(pred["actual_cell_peak"],16)
                fixed=C.fixed_result("fixed_consistency16",g)
                self.assertFalse(fixed["blocked"])
                self.assertLessEqual(fixed["actual_cell_peak"],16)
            self.assertTrue(C.fixed_result("fixed_consistency16",pos)["prediction"])
            self.assertFalse(C.fixed_result("fixed_consistency16",neg)["prediction"])

    def test_genuine_fit_gradient_and_three_field_state(self):
        initial=L.init_codebook()
        self.assertEqual(len(set(initial)),16)
        data=L.training_examples()
        self.assertEqual(len(data),288)
        self.assertTrue(any(label==0 for _,_,label in data))
        self.assertTrue(any(label==1 for _,_,label in data))
        self.assertEqual(L.EPOCHS,100)
        self.assertEqual(L.PARAMETER_COUNT,17)
        self.assertEqual(C.ARMS[:6],("O_original","O_combined",
                                    "U_original","U_combined",
                                    "untrained_fp","trained_fp"))

if __name__=="__main__":unittest.main()
