"""F124-AE pinned new-source families, original bytecode and fixed 16-cell model."""
import json,unittest
import f124ae_source as source
import f124ae_transfer_evidence as transfer
import f124ad_intermediate_credit as AD
import f124o_native_learners as O

class F124AEFreezes(unittest.TestCase):
    def test_preimplementation_blob_and_exact_qualified_original(self):
        self.assertEqual(len(source.frozen()),64)
        p=json.loads(source.PROTOCOL.read_text())
        self.assertEqual(p["parent"]["exact_head"],
                         "64735ba011d235f4a040ef30135735f9008d896a")
        self.assertEqual(p["parent"]["qualified_run"],39108375190)
        self.assertEqual(p["models"]["coefficients"],{"gamma":0.1,"penalty":1})
        self.assertTrue(all(v is False for v in p["governance"].values()))
        self.assertEqual(len(set(source.SALTS.values())),4)
        self.assertEqual(transfer.COEFFICIENTS,{"gamma":0.1,"penalty":1.0})
        with self.assertRaises(source.Quarantined):source.protected()

    def test_new_transfer_FIT_DEV_full_balanced_pairs(self):
        for family in source.FAMILIES:
            lane="AE_"+family
            self.assertTrue(set(source.COHORTS[lane]["FIT"]).isdisjoint(
                            source.COHORTS[lane]["DEV"]))
            for phase in ("FIT","DEV"):
                strata={10:0,11:0,12:0}
                for vec in source.VECTORS:
                    for seed in source.COHORTS[lane][phase]:
                        pos,neg=source.transfer_pair(seed,vec,phase,family)
                        self.assertTrue(source.paired_admit(pos,neg))
                        strata[len(pos["roles"])]+=1
                self.assertEqual(strata,{10:16,11:16,12:16},msg=family+phase)

    def test_old_original_models_and_new_16cell_budget(self):
        weights={"base":list(O.YGGDRASIL_INIT),
                 "R":[.02,-.01],"S":[.02,.01],"U":[.1,-.08]}
        for family in source.FAMILIES:
            seed=source.COHORTS["AE_"+family]["FIT"].start
            positive,negative=source.transfer_pair(seed,[2,1,1],"FIT",family)
            for arm in ("O","U"):
                for graph in (positive,negative):
                    base=AD.forward(arm,graph,weights,gamma=0.,penalty=0.)
                    combined=AD.forward(arm,graph,weights,gamma=.1,penalty=1.)
                    self.assertTrue(base["logit_hex"].startswith(("0x","-0x")))
                    self.assertLessEqual(combined["final_active"],7)
                    self.assertLessEqual(combined["final_retained"],9)
                    self.assertLessEqual(combined["final_active"]+
                                         combined["final_retained"],16)
                route=AD.exact_positive_prefix(positive)
                original=AD.forward(arm,positive,weights,gamma=.1,penalty=1.)
                inspect=AD.forward(arm,positive,weights,positive_prefix=route,
                                   gamma=.1,penalty=1.)
                self.assertEqual(original["logit_hex"],inspect["logit_hex"])

    def test_strong_fixed_original_python_bytecode(self):
        fn=transfer.strong_fixed_12of16()
        import f124h_train_receipt as H
        self.assertIs(fn.__code__,H.fixed_comparator.__code__)
        self.assertEqual(transfer.ARMS,("O_original","O_combined",
                                        "U_original","U_combined"))
        self.assertEqual(transfer.FAMILIES,
                         ("rekey","rewire","near_break","late_break"))

if __name__=="__main__":
    unittest.main()
