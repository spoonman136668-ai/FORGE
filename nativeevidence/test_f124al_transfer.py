"""F124-AL focused identity, semantic conservation, model code lock and
honestly qualified bounded fixed controls on both Windows and Ubuntu."""
import json,unittest
import f124al_transfer_source as S
import f124al_transfer as T
import f124ak_learned as AK

class NewOperatorTransferFrozen(unittest.TestCase):
    def test_frozen_preregistration_and_original_FIT_receipt_identity(self):
        self.assertEqual(len(S.frozen()),64)
        protocol=json.loads(S.PROTOCOL.read_text())
        self.assertEqual(protocol["parent"]["qualified_head"],
                         "6b1e0dc9a9a8e971bdcc042ca54db4d88d8dfe0d")
        self.assertEqual(protocol["parent"]["actions"],39116272361)
        self.assertEqual(protocol["locked_model"]["FIT_receipt_SHA256"],
                         T.TRAIN_SHA)
        self.assertEqual(protocol["physical"]["new_process_repetitions"],3)
        self.assertTrue(all(not v for v in protocol["governance"].values()))
        with self.assertRaises(S.Quarantined):S.protected()

    def test_new_FIT_DEV_sources_are_disjoint_and_all_pairs_balanced(self):
        for family in S.FAMILIES:
            self.assertTrue(set(S.COHORTS[family]["FIT"]).isdisjoint(
                            S.COHORTS[family]["DEV"]))
            depth_counter={}
            for phase in ("FIT","DEV"):
                depth_counter={10:0,11:0,12:0}
                for v in S.VECTORS:
                    for seed in S.COHORTS[family][phase]:
                        p,n=S.build(family,seed,v,phase)
                        self.assertTrue(S.admit(p,n))
                        depth_counter[len(p["roles"])]+=1
                self.assertEqual(depth_counter,{10:16,11:16,12:16})

    def test_original_AK_python_code_frozen_and_original_state_16(self):
        original=T.ak_original()
        self.assertIs(original.__code__,AK.infer.__code__)
        model=AK.seeded()
        self.assertEqual(AK.count_params(model),38)
        for family in S.FAMILIES:
            pos,neg=S.build(family,3390000,[2,1,1],"FIT")
            for g in (pos,neg):
                prediction=original(g,model,.1)
                self.assertLessEqual(prediction["actual_cell_peak"],16)
                for ctrl in (T.old_fixed_consistency,T.old_fixed_collisionfree,
                             T.generalized):
                    result=ctrl(g)
                    self.assertFalse(result["blocked"],family+ctrl.__name__)
                    self.assertLessEqual(result["actual_cell_peak"],16)
            self.assertTrue(T.generalized(pos)["prediction"])
            self.assertFalse(T.generalized(neg)["prediction"])

    def test_expanded_operator_causal_oracle_is_evaluator_only(self):
        self.assertEqual(S.WIDTH["double_bit"],2)
        self.assertEqual(len(S.HOPS["three_events"]),3)
        self.assertEqual(S.HOPS["silent_slot"],(2,8))
        silence=json.loads(S.PROTOCOL.read_text())["source"]["families"][1]
        self.assertEqual(silence["silent"],5)
        self.assertEqual(T.ARMS,("ak_original_frozen","fixed_consistency16",
            "fixed_collisionfree","fixed_generalized_mask"))
        for family in S.FAMILIES:
            pos,neg=S.build(family,3390100,[1,2,1],"DEV")
            self.assertEqual(S.semantic_routes(pos),1)
            self.assertEqual(S.semantic_routes(neg),0)
            self.assertEqual(S.semantic_routes(pos,"exact"),0)
            self.assertEqual(S.semantic_routes(neg,"exact"),0)
            self.assertGreaterEqual(S.semantic_routes(pos,"role_only"),1)

if __name__=="__main__":unittest.main()
