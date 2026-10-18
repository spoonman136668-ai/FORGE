"""F124-AA independent frozen transfer and instrument ablation regression."""
import json
import math
import unittest

import f124aa_source as src
import f124aa_ygg_transfer as Y
import f124aa_wing_ablation as W
import f124o_native_learners as O
import f124v_yggdrasil_causal_trace as V


class F124AAQualification(unittest.TestCase):
    def test_exact_freeze_and_independent_new_development_sources(self):
        self.assertEqual(len(src.frozen()),64)
        p=json.loads(src.PROTOCOL.read_text())
        self.assertEqual(p["qualified_parent"]["merged_branch_sha"],
                         "c98fceb45200d65fc5be6d83ab9964bb1eaa5865")
        self.assertEqual(p["qualified_parent"]["qualified_run"],39090043467)
        self.assertEqual([v["key"] for v in p["Y_transfer"]["families"]],
                          ["rekey","rewire","long_depth"])
        self.assertEqual(p["W_ablation"]["instruments"],["none","tracemalloc"])
        self.assertTrue(all(v is False for v in p["governance"].values()))
        with self.assertRaises(src.Quarantined):
            src.protected()

    def test_all_three_new_families_public_pair_and_fixed_denominators(self):
        for phase in ("FIT","DEV"):
            for family in Y.FAMILIES:
                depths={}
                for vector in src.VECTORS:
                    for seed in src.COHORTS["YggdrasilStress"][phase]:
                        p,n=src.transfer_pair(seed,vector,phase,family)
                        self.assertTrue(src.paired_admit(p,n))
                        dep=len(p["roles"])
                        depths[dep]=depths.get(dep,0)+1
                expected={10:16,11:16,12:16} if family=="long_depth" else {
                    7:16,8:16,9:16}
                self.assertEqual(depths,expected)

    def test_new_policies_blind_to_evaluator_and_original_model_same_under_9(self):
        w={"base":list(O.YGGDRASIL_INIT),"R":[.12,-.03],
           "S":[.09,.12],"U":[.07,-.08]}
        for family in Y.FAMILIES:
            p,n=src.transfer_pair(1790000,[2,1,1],"FIT",family)
            for graph in (p,n):
                for arm in Y.ARMS:
                    a=Y.forward(arm,graph,w,"original")
                    b=Y.forward(arm,graph,w,"diverse")
                    self.assertTrue(math.isfinite(float.fromhex(b["logit_hex"])))
                    self.assertLessEqual(b["final_active"],7)
                    self.assertLessEqual(b["final_retained"],9)
                    if family!="long_depth":
                        orig,_=V.original_forward(arm,graph,w)
                        self.assertEqual(a["logit_hex"],orig.hex())
            route=Y.exact_positive_prefix(p)
            self.assertEqual(len(route),len(p["roles"]))
            for arm in Y.ARMS:
                for mode in Y.MODES:
                    before=Y.forward(arm,p,w,mode)
                    after=Y.forward(arm,p,w,mode,route)
                    self.assertEqual(before["logit_hex"],after["logit_hex"])

    def test_wing_ablation_same_inference_only_instrumentation_and_caps(self):
        self.assertEqual(W.CAPS,(24,22,20))
        self.assertEqual(W.ARMS,("S_packed","T_full_index","U_microindex"))
        self.assertEqual(W.STAGES,("pre_import","after_import","after_fixtures",
                       "after_cap_attach","after_warmup","after_inference"))
        p=json.loads(src.PROTOCOL.read_text())
        self.assertEqual(p["W_ablation"]["repetitions"],2)
        self.assertTrue(p["W_ablation"]["same_host_per_OS"])


if __name__=="__main__":
    unittest.main()
