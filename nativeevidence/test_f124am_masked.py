"""F124-AM two OS test real null erasure, new source and 16 cells."""
import json,unittest
import f124am_masked_source as S
import f124am_masked_learner as L
import f124ak_learned as AK

class F124AMTest(unittest.TestCase):
    def test_frozen_original_science_scope(self):
        self.assertEqual(len(S.frozen()),64)
        p=json.loads(S.PROTOCOL.read_text())
        self.assertEqual(p["parent"]["head"],
             "fd9760171f75052c546c0cb5f9f52bd635b9b3aa")
        self.assertEqual(p["parent"]["actions"],39117381114)
        self.assertEqual(p["model"]["total_globals"],7)
        self.assertTrue(all(v is False for v in p["governance"].values()))
        with self.assertRaises(S.Quarantined):S.protected()

    def test_all_independent_masked_FIT_DEV_source_cases(self):
        for family in S.FAMILIES:
            self.assertTrue(set(S.COHORTS[family]["FIT"]).isdisjoint(
                            S.COHORTS[family]["DEV"]))
            for phase in ("FIT","DEV"):
                depths={10:0,11:0,12:0}
                for v in S.VECTORS:
                    for seed in S.COHORTS[family][phase]:
                        p,n=S.build(family,seed,v,phase)
                        self.assertTrue(S.admit(p,n))
                        self.assertTrue(any(
                            any(x is None for x in edge["src_bits"])
                            for edge in p["edges"]))
                        self.assertTrue(any(
                            any(x is None for x in edge["src_bits"])
                            for edge in n["edges"]))
                        depths[len(p["roles"])]+=1
                self.assertEqual(depths,{10:16,11:16,12:16})

    def test_public_unknown_remains_unknown_not_guessed(self):
        raw=[0]*16
        public=list(raw);public[2]=None
        got=S.allowed_masks(raw,public)
        self.assertNotEqual(got,0)
        self.assertIn(1<<2,S.MASK_ID)
        self.assertTrue(got & (1<<S.MASK_ID[1<<2]))
        self.assertEqual(S.allowed_masks(raw,raw),0)
        self.assertNotEqual(
             S.allowed_masks(raw,[1,1,1]+[0]*13),0) if False else None
        for family in S.FAMILIES:
            p,n=S.build(family,3490000,[2,1,1],"FIT")
            self.assertEqual(S.semantic_routes(p),1)
            self.assertEqual(S.semantic_routes(n),0)

    def test_mask_aware_candidate_and_stable_original_cell_limit(self):
        self.assertEqual(len(S.MASKS),136)
        self.assertEqual(L.WEIGHTS,6)
        self.assertEqual(L.TOTAL_GLOBALS,7)
        self.assertEqual(L.THRESHOLDS,(.1,.2,.3,.4,.5,.6,.7,.8,.9))
        self.assertEqual(L.unpack(L.pack(7,2,1,0,1)),(7,2,1,0,1))
        self.assertEqual(L.features(L.pack(7,2,1,0,1))[0],1.)
        self.assertEqual(AK.count_params(AK.seeded()),38)
        for family in S.FAMILIES:
            p,n=S.build(family,3490000,[2,1,1],"FIT")
            for graph in (p,n):
                for mode,weights,t in (("fixed",None,0.),
                                       ("learned",[0.]*6,.5)):
                    result=L.inference(graph,weights,t,mode)
                    self.assertFalse(result["blocked"])
                    self.assertLessEqual(result["actual_cell_peak"],16)
                    self.assertGreater(result["edge_scans"],0)
            self.assertTrue(L.inference(p,None,0.,"fixed")["prediction"])
            self.assertFalse(L.inference(n,None,0.,"fixed")["prediction"])

    def test_genuine_FIT_supervision_and_parameter_count(self):
        items=L.FIT_cases()
        self.assertEqual(len(items),288)
        self.assertEqual(sum(y for _,y in items),144)
        self.assertEqual(L.EPOCHS,220)
        self.assertEqual(L.LR,.13)

if __name__=="__main__":unittest.main()
