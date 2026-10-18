"""F124-AN preregistration, source-identifiability and original capacity tests."""
import json,unittest
import f124an_observable_source as S
import f124an_identifiability as M
class F124ANFrozen(unittest.TestCase):
    def test_preimplementation_custody_and_science_guard(self):
        self.assertEqual(len(S.frozen()),64)
        p=json.loads(S.PROTOCOL.read_text())
        self.assertEqual(p["phase"],"PREIMPLEMENTATION_FROZEN")
        self.assertEqual(p["parent"]["head"],"16af9d9175052856c54e20bd886aa49660c4b392")
        self.assertEqual(p["parent"]["qualifying_actions"],39118421276)
        self.assertEqual(p["model"]["state"]["max_total"],16)
        self.assertEqual(p["model"]["training"]["epochs"],160)
        self.assertEqual(p["model"]["trained_head"].split(" ")[0],"three-way")
        self.assertTrue(all(v is False for v in p["governance"].values()))
        with self.assertRaises(S.Quarantined):S.protected()

    def test_all_new_independent_FIT_DEV_born_before_modelling(self):
        for family in S.FAMILIES:
            self.assertTrue(set(S.COHORTS[family]["FIT"]).isdisjoint(
                           S.COHORTS[family]["DEV"]))
            for phase in ("FIT","DEV"):
                depths={10:0,11:0,12:0}
                for v in S.VECTORS:
                    for seed in S.COHORTS[family][phase]:
                        d=S.build(family,seed,v,phase)
                        self.assertEqual(S.judgment(d["positive"]),"POS")
                        self.assertEqual(S.judgment(d["negative"]),"NEG")
                        self.assertEqual(S.witness(d["ambiguous_public"]),{True,False})
                        self.assertEqual(S.judgment(d["ambiguous_public"]),"ABSTAIN")
                        self.assertEqual(json.dumps(d["ambiguous_public"],sort_keys=True),
                                         json.dumps(d["ambiguous_twin"],sort_keys=True))
                        self.assertTrue(any(None in e["src_bits"]
                                for e in d["ambiguous_public"]["edges"]))
                        depths[len(d["positive"]["roles"])]+=1
                self.assertEqual(depths,{10:16,11:16,12:16})

    def test_bounded_public_belief_controls_no_hidden_world(self):
        self.assertEqual(M.num_weights(M.seeded()),15)
        self.assertEqual(M.GLOBAL_PARAMS,16)
        self.assertEqual(M.THRESHOLDS,(.4,.5,.6,.7,.8,.9,.95))
        for family in S.FAMILIES:
            d=S.build(family,3590000,[2,1,1],"FIT")
            for kind,expected in (("positive","POS"),("negative","NEG"),
                                   ("ambiguous_public","ABSTAIN"),
                                   ("ambiguous_twin","ABSTAIN")):
                ob=M.observe(d[kind])
                self.assertEqual(ob["deterministic"],expected)
                self.assertLessEqual(ob["cell_peak"],16)
                self.assertGreater(ob["edge_scans"],0)
                answer,_=M.decide(ob,None,0.,"fixed")
                self.assertEqual(answer,expected)
            self.assertEqual(M.observe(d["ambiguous_public"])["feature"],
                             M.observe(d["ambiguous_twin"])["feature"])

    def test_training_FIT_only_three_class_balance(self):
        records=M.training_data()
        self.assertEqual(len(records),432)
        for label in range(3):
            self.assertEqual(sum(y==label for _,y in records),144)

if __name__=="__main__":unittest.main()
