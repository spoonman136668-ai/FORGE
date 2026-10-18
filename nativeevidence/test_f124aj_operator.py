"""F124-AJ cross-platform frozen source, actual raw neural operator and caps."""
import json,math,unittest
import f124aj_source as S
import f124aj_raw_neural as N
import f124aj_comparison as C
import f124ad_intermediate_credit as AD
import f124o_native_learners as O
class F124AJChecks(unittest.TestCase):
    def test_original_preregistration_and_protection(self):
        self.assertEqual(len(S.frozen()),64)
        p=json.loads(S.PROTOCOL.read_text())
        self.assertEqual(p["qualified_parent"]["head"],
          "b39785756f7f587867930c34023986296455b077")
        self.assertEqual(p["qualified_parent"]["run"],39113708960)
        self.assertEqual(p["architecture"]["model_params"]["total"],50)
        self.assertEqual(p["architecture"]["training"]["epochs"],140)
        self.assertTrue(all(v is False for v in p["governance"].values()))
        with self.assertRaises(S.Quarantined):S.protected()

    def test_all_new_frozen_FIT_DEV_source_pairs_and_strata(self):
        for fam in S.FAMILIES:
            self.assertTrue(set(S.COHORTS[fam]["FIT"]).isdisjoint(
                            S.COHORTS[fam]["DEV"]))
            for phase in ("FIT","DEV"):
                depths={10:0,11:0,12:0}
                for vector in S.VECTORS:
                    for seed in S.COHORTS[fam][phase]:
                        p,n=S.build(fam,seed,vector,phase)
                        self.assertTrue(S.paired_admit(p,n))
                        depths[len(p["roles"])]+=1
                self.assertEqual(depths,{10:16,11:16,12:16})

    def test_real_raw_bit_operator_not_supplied_index(self):
        model=N.seeded()
        self.assertEqual(N.count_params(model),49)
        self.assertEqual(sum(N.raw_patterns(
            [0]*16,[1]*16,[1]*16,[0]*16)),16)
        self.assertEqual(N.bits16(N.bitint([1,0]*8)),[1,0]*8)
        x=[0]*16;y=[0]*16;y[3]=1
        packed=N.pack(x,y)
        self.assertTrue(packed>=N.PACK_FLAG)
        self.assertEqual(N.unpack(packed),(x,y))
        p,_,_=N.network(model,N.raw_patterns(x,y,x,y),True)
        self.assertTrue(math.isfinite(p) and 0<p<1)
        self.assertEqual(N.PARAMS,49)
        self.assertEqual(N.THRESHOLDS,
            (.05,.1,.2,.3,.4,.5,.6,.7,.8,.9,.95))
        self.assertIs(C.original().__code__,AD.forward.__code__)

    def test_original_16_slots_and_strong_fixed_controls_complete(self):
        model=N.seeded()
        weights={"base":list(O.YGGDRASIL_INIT),"R":[.02,-.01],
                 "S":[.02,.04],"U":[.02,-.06]}
        for family in S.FAMILIES:
            p,n=S.build(family,3190000,[2,1,1],"FIT")
            self.assertEqual(S.semantic_routes(p),1)
            self.assertEqual(S.semantic_routes(n),0)
            for g in (p,n):
                for score in (.05,.95):
                    pred=N.infer(g,model,score)
                    self.assertLessEqual(pred["actual_cell_peak"],16)
                for fixed in (C.fixed_consistency,C.fixed_collisionfree):
                    v=fixed(g)
                    self.assertFalse(v["blocked"])
                    self.assertLessEqual(v["actual_cell_peak"],16)
                for who in ("O","U"):
                    historical=C.original()(who,g,weights,gamma=.1,penalty=1.)
                    self.assertLessEqual(historical["final_active"],7)
                    self.assertLessEqual(historical["final_retained"],9)
            self.assertTrue(C.fixed_consistency(p)["prediction"])
            self.assertFalse(C.fixed_consistency(n)["prediction"])
            self.assertTrue(C.fixed_collisionfree(p)["prediction"])
            self.assertFalse(C.fixed_collisionfree(n)["prediction"])
if __name__=="__main__":unittest.main()
