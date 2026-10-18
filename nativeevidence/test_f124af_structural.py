"""F124-AF structural source birth and comparator fairness tests on both OS."""
import json,unittest
import f124af_sparse_source as src
import f124af_fixed_controls as E
import f124h_train_receipt as H
import f124ad_intermediate_credit as AD
import f124o_native_learners as O

class StructuralQualification(unittest.TestCase):
    def test_preimplementation_and_nonprotected(self):
        self.assertEqual(len(src.frozen()),64)
        p=json.loads(src.PROTOCOL.read_text())
        self.assertEqual(p["qualified_parent"]["head"],
                         "8eede780f027882c2c4e12b0452f78c99ebe0e64")
        self.assertEqual(p["qualified_parent"]["actions"],39109580026)
        self.assertEqual(p["models"]["frozen_gamma"],.1)
        self.assertEqual(p["models"]["frozen_penalty"],1.)
        self.assertEqual(p["resources"]["fresh_repetitions"],3)
        self.assertTrue(all(v is False for v in p["governance"].values()))
        with self.assertRaises(src.Quarantined):src.protected()

    def test_all_new_FIT_DEV_48_pairs_and_original_H12_always_completes(self):
        control=E.historical_H12()
        self.assertIs(control.__code__,H.fixed_comparator.__code__)
        for family in src.FAMILIES:
            for phase in ("FIT","DEV"):
                depths={10:0,11:0,12:0}
                for vector in src.VECTORS:
                    for seed in src.COHORTS[family][phase]:
                        positive,negative=src.build(family,seed,vector,phase)
                        self.assertTrue(src.paired_admit(positive,negative))
                        depths[len(positive["roles"])]+=1
                        for graph in (positive,negative):
                            r=E.H12(graph,control)
                            self.assertFalse(r["blocked"],msg=family+phase)
                            self.assertTrue(r["edge_scans"]>0)
                self.assertEqual(depths,{10:16,11:16,12:16})

    def test_bounded_fixed_same_original_cell_fields_and_capacity(self):
        fn=E.prior_model()
        self.assertIs(fn.__code__,AD.forward.__code__)
        w={"base":list(O.YGGDRASIL_INIT),"R":[.02,.05],
           "S":[.02,-.04],"U":[.03,-.07]}
        for family in src.FAMILIES:
            positive,negative=src.build(family,2790000,[2,1,1],"FIT")
            for graph in (positive,negative):
                ref=E.bounded_exact16(graph)
                self.assertFalse(ref["blocked"])
                self.assertLessEqual(ref["actual_cell_peak"],16)
                self.assertGreater(ref["edge_scans"],0)
                for who in ("O","U"):
                    for params in ({},{"gamma":.1,"penalty":1.}):
                        got=fn(who,graph,w,**params)
                        self.assertLessEqual(got["final_active"],7)
                        self.assertLessEqual(got["final_retained"],9)
                        self.assertLessEqual(got["final_active"]+
                                             got["final_retained"],16)

    def test_all_four_original_model_arms_and_unmodified_coefficient(self):
        self.assertEqual(E.ARMS,("O_original","O_combined",
                                 "U_original","U_combined"))
        self.assertEqual(E.GAMMA,.1)
        self.assertEqual(E.PENALTY,1.)
        self.assertEqual(src.FAMILIES,
                         ("sparse_diamond","role_reuse","terminal_decoy"))

if __name__=="__main__":unittest.main()
