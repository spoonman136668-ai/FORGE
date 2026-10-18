"""F124-AA frozen orthogonal transfer and matched diagnostic gate."""
import json, unittest
import f124aa_source as source
import f124aa_ygg_transfer as model
import f124aa_ygg_cost as cost
import f124aa_wing_ablation as wing
import f124v_yggdrasil_causal_trace as original
import f124o_native_learners as O

class TestF124AA(unittest.TestCase):
    def test_exact_first_freeze_and_no_science_promotion(self):
        self.assertEqual(len(source.frozen()),64)
        p=json.loads(source.PROTOCOL.read_text())
        self.assertEqual(p["parent"]["merge_PR"],494)
        self.assertEqual(p["parent"]["qualified_F124Z_run"],39090043467)
        self.assertEqual(p["ygg_transfer"]["benchmark"]["runs_each_arm"],2)
        self.assertEqual(p["wing_instrumentation"]["instrumentation"],
                         ["off","tracemalloc_only"])
        self.assertTrue(all(v is False for v in p["governance"].values()))
        with self.assertRaises(source.Quarantined):source.protected()

    def test_independent_new_birth_and_true_pair_labels(self):
        for lane in ("Wingless","YggdrasilStress"):
            self.assertTrue(set(source.COHORTS[lane]["FIT"]).isdisjoint(
                            source.COHORTS[lane]["DEV"]))
            for phase in ("FIT","DEV"):
                depth={7:0,8:0,9:0}
                for vector in source.VECTORS:
                    for seed in source.COHORTS[lane][phase]:
                        if lane=="YggdrasilStress":
                            pos,neg=source.stress_pair(seed,vector,phase)
                        else:pos,neg=source.build(lane,seed,vector,phase)
                        self.assertTrue(source.paired_admit(pos,neg))
                        depth[len(pos["roles"])]+=1
                self.assertEqual(depth,{7:16,8:16,9:16})

    def test_source_original_logits_and_diversity_budget(self):
        weights={"base":list(O.YGGDRASIL_INIT),
                 "R":[.09,-.02],"S":[.04,.03],"U":[.07,-.02]}
        positive,negative=source.stress_pair(1790000,[2,1,1],"FIT")
        route=original.exact_positive_prefix(positive)
        for arm in ("O","U"):
            for graph in (positive,negative):
                original_score,_=original.original_forward(arm,graph,weights)
                new=model.forward(arm,graph,weights,"original",route if graph is positive else None)
                self.assertEqual(original_score.hex(),new["logit_hex"])
                diverse=model.forward(arm,graph,weights,"diverse")
                self.assertTrue(diverse["logit_hex"].startswith(("0x","-0x")))
                self.assertLessEqual(diverse["final_active"],7)
                self.assertLessEqual(diverse["final_retained"],9)
            seen=model.forward(arm,positive,weights,"diverse",route)
            self.assertEqual(len(seen["hops"]),len(positive["roles"]))

    def test_resource_and_stage_controls_are_independent(self):
        self.assertEqual(wing.CAPS,(28,24,20))
        self.assertEqual(wing.ARMS,("S_packed","T_full_index","U_microindex"))
        self.assertEqual(wing.STAGES[-1],"after_inference")
        self.assertEqual(len(cost.ARMS),4)
        self.assertIn("tracemalloc_only",source.PROTOCOL.read_text())

if __name__=="__main__":
    unittest.main()
