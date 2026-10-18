"""F124-AG source birth, ambiguity and finite 16-cell comparator tests."""
import json,unittest
import f124ag_noisy_source as S
import f124ag_noisy_controls as C
import f124ad_intermediate_credit as AD
import f124h_train_receipt as H
import f124o_native_learners as O

class F124AGFrozenScience(unittest.TestCase):
    def test_freeze_and_no_protected_source(self):
        self.assertEqual(len(S.frozen()),64)
        f=json.loads(S.PROTOCOL.read_text())
        self.assertEqual(f["qualified_parent"]["head"],
                         "5ca3596ba07ac30ea313544b93dfd035062dc051")
        self.assertEqual(f["models"]["gamma"],.1)
        self.assertEqual(f["models"]["penalty"],1.)
        self.assertTrue(all(x is False for x in f["governance"].values()))
        with self.assertRaises(S.Quarantined):S.protected()

    def test_every_source_is_genuinely_noisy_and_paired_all_depths(self):
        for family in S.FAMILIES:
            self.assertTrue(set(S.COHORTS[family]["FIT"]).isdisjoint(
                            S.COHORTS[family]["DEV"]))
            for phase in ("FIT","DEV"):
                depths={10:0,11:0,12:0}
                for vector in S.VECTORS:
                    for seed in S.COHORTS[family][phase]:
                        p,n=S.build(family,seed,vector,phase)
                        self.assertTrue(S.paired_admit(p,n))
                        depths[len(p["roles"])]+=1
                        self.assertEqual(S.routes(p,"consistency"),1)
                        self.assertEqual(S.routes(n,"consistency"),0)
                        self.assertEqual(S.routes(p,"exact16"),0)
                        self.assertEqual(S.routes(n,"exact16"),0)
                        self.assertEqual(S.routes(p,"tolerant15"),1)
                        self.assertEqual(S.routes(n,"tolerant15"),1)
                self.assertEqual(depths,{10:16,11:16,12:16})

    def test_history_is_bit_identical_and_new_controls_fit_16_cells(self):
        original=C.original_forward()
        strong=C.H12()
        self.assertIs(original.__code__,AD.forward.__code__)
        self.assertIs(strong.__code__,H.fixed_comparator.__code__)
        w={"base":list(O.YGGDRASIL_INIT),
           "R":[.01,-.01],"S":[.02,.04],"U":[.08,-.03]}
        for family in S.FAMILIES:
            p,n=S.build(family,2890000,[2,1,1],"FIT")
            for g in (p,n):
                for arm in ("O","U"):
                    base=original(arm,g,w)
                    combined=original(arm,g,w,gamma=.1,penalty=1.)
                    self.assertLessEqual(base["final_active"]+
                                         base["final_retained"],16)
                    self.assertLessEqual(combined["final_active"]+
                                         combined["final_retained"],16)
                for control in C.CONTROLS:
                    z=C.control_result(control,g)
                    self.assertFalse(z["blocked"],msg=family+control)
                    self.assertGreater(z["edge_scans"],0)
                    if control!="H12":
                        self.assertLessEqual(z["actual_cell_peak"],16)
            self.assertFalse(C.control_result("fixed_exact16",p)["prediction"])
            self.assertTrue(C.control_result("fixed_tolerant15",p)["prediction"])
            self.assertTrue(C.control_result("fixed_tolerant15",n)["prediction"])
            self.assertTrue(C.control_result("fixed_consistency16",p)["prediction"])
            self.assertFalse(C.control_result("fixed_consistency16",n)["prediction"])

    def test_prior_and_new_comparators_are_separate(self):
        self.assertEqual(C.ARMS,("O_original","O_combined",
                                 "U_original","U_combined"))
        self.assertEqual(C.CONTROLS,("fixed_exact16","fixed_tolerant15",
                                     "fixed_consistency16","H12"))
        self.assertEqual(C.GAMMA,.1);self.assertEqual(C.PENALTY,1.)

if __name__=="__main__":unittest.main()
