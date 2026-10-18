"""F124-AK two-platform original source/SCI and learned-hop invariants."""
import json,math,unittest
import f124ak_source as S
import f124ak_learned as L
import f124ak_comparison as C
import f124ad_intermediate_credit as AD
import f124o_native_learners as O

class FrozenIntermediateOperator(unittest.TestCase):
    def test_protocol_frozen_before_code_and_zero_protected_first_use(self):
        self.assertEqual(len(S.frozen()),64)
        p=json.loads(S.PROTOCOL.read_text())
        self.assertEqual(p["stage"],"PREIMPLEMENTATION_FROZEN")
        self.assertEqual(p["qualified_parent"]["head"],
                         "9aa122181ce517f4e6967e752d8aff337c77d01c")
        self.assertEqual(p["qualified_parent"]["run"],39114981482)
        self.assertEqual(p["training"]["local_epochs"],320)
        self.assertEqual(p["training"]["binder_epochs"],360)
        self.assertEqual(p["architecture"]["total_global_params"],39)
        self.assertTrue(all(v is False for v in p["governance"].values()))
        with self.assertRaises(S.Quarantined):S.protected()

    def test_all_new_FIT_and_DEV_pair_inventories_and_depths(self):
        for family in S.FAMILIES:
            self.assertTrue(set(S.COHORTS[family]["FIT"]).isdisjoint(
                            S.COHORTS[family]["DEV"]))
            for phase in ("FIT","DEV"):
                counts={10:0,11:0,12:0}
                for v in S.VECTORS:
                    for seed in S.COHORTS[family][phase]:
                        p,n=S.build(family,seed,v,phase)
                        self.assertTrue(S.admit(p,n))
                        counts[len(p["roles"])]+=1
                self.assertEqual(counts,{10:16,11:16,12:16})

    def test_model_39_trainable_global_weights_and_original_cells(self):
        m=L.seeded()
        self.assertEqual(L.count_params(m),39)
        self.assertEqual(len(L.predict_table(m["local"])),4)
        self.assertEqual(L.mask_from_raw([0]*16,[1]*16,{
              (0,0):0.,(0,1):1.,(1,0):1.,(1,1):0.}),65535)
        self.assertEqual(L.relation_features(1,1),(1.,0.,0.,1.))
        self.assertEqual(L.relation_features(1,2),(0.,1.,1.,0.))
        self.assertEqual(L.THRESHOLDS,(.1,.2,.3,.4,.5,.6,.7,.8,.9))
        self.assertEqual(L.SENTINEL,65536)
        self.assertIs(C.old_original().__code__,AD.forward.__code__)
        w={"base":list(O.YGGDRASIL_INIT),"R":[.02,.01],
           "S":[.04,-.02],"U":[.02,.03]}
        for family in S.FAMILIES:
            pos,neg=S.build(family,3290000,[2,1,1],"FIT")
            for graph in (pos,neg):
                for confidence in (.1,.9):
                    result=L.infer(graph,m,confidence)
                    self.assertLessEqual(result["actual_cell_peak"],16)
                    self.assertTrue(result["packed_first_mask_in_original_score"])
                for ctrl in (C.fixed_consistency,C.fixed_collisionfree):
                    result=ctrl(graph)
                    self.assertFalse(result["blocked"])
                    self.assertLessEqual(result["actual_cell_peak"],16)
                for old in ("O","U"):
                    result=C.old_original()(old,graph,w,gamma=.1,penalty=1.)
                    self.assertLessEqual(result["final_active"],7)
                    self.assertLessEqual(result["final_retained"],9)
            self.assertTrue(C.fixed_consistency(pos)["prediction"])
            self.assertFalse(C.fixed_consistency(neg)["prediction"])
            self.assertTrue(C.fixed_collisionfree(pos)["prediction"])
            self.assertFalse(C.fixed_collisionfree(neg)["prediction"])

    def test_intermediate_FIT_path_supervision_from_public_edges_only(self):
        data,distribution=L.fit_examples()
        self.assertEqual(len(data),288)
        self.assertEqual(sum(y for _,y in data),144)
        self.assertEqual(sum(distribution.values()),288*2*16)
        self.assertTrue(all(v>0 for v in distribution.values()))
        self.assertEqual(L.LOCAL_PARAMS,33)
        self.assertEqual(L.HEAD_PARAMS,5)
        self.assertEqual(L.TOTAL_PARAMS,39)

if __name__=="__main__":unittest.main()
