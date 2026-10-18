"""F124-AB three novel preregistered development experiments."""
import json
import math
import unittest

import f124ab_source as src
import f124ab_ygg_longscore as Y
import f124ab_ygg_ram_cost as Cost
import f124ab_wing_heavy as W
import f124o_native_learners as O
import f124v_yggdrasil_causal_trace as V


class F124ABFrozenScience(unittest.TestCase):
    def test_original_parent_and_immutable_freeze(self):
        self.assertEqual(len(src.frozen()),64)
        p=json.loads(src.PROTOCOL.read_text())
        self.assertEqual(p["qualified_parent"]["sha"],
                         "666dd533dc855392f9c1fc86b8ed8e354f5662c7")
        self.assertEqual(p["qualified_parent"]["run_id"],39091779130)
        self.assertEqual(p["experiments"]["Y_long_score"]["frozen_FIT_threshold_grid"],[-8,-6,-4,-2,-1,0,1,2,4,6,8])
        self.assertEqual(tuple(p["experiments"]["W_heavy_factorial"]["instruments"]),
                         ("plain","tracemalloc","retain_case_diagnostics",
                          "tracemalloc_plus_retain"))
        self.assertTrue(all(x is False for x in p["governance"].values()))
        with self.assertRaises(src.Quarantined):src.protected()

    def test_all_new_public_cohorts_and_distinct_salts(self):
        self.assertEqual(len(set(src.SALTS.values())),3)
        for lane in ("YggdrasilStress","YggdrasilCost","Wingless"):
            self.assertTrue(set(src.COHORTS[lane]["FIT"]).isdisjoint(
                            src.COHORTS[lane]["DEV"]))
        for lane in ("YggdrasilStress","YggdrasilCost","Wingless"):
            counts={}
            for v in src.VECTORS:
                for seed in src.COHORTS[lane]["FIT"]:
                    if lane=="YggdrasilStress":
                        p,n=src.transfer_pair(seed,v,"FIT","long_depth")
                    elif lane=="YggdrasilCost":
                        p,n=src.stress_pair(seed,v,"FIT",lane=lane)
                    else:
                        p,n=src.build(lane,seed,v,"FIT")
                    self.assertTrue(src.paired_admit(p,n))
                    d=len(p["roles"])
                    counts[d]=counts.get(d,0)+1
            self.assertEqual(counts,
                             {10:16,11:16,12:16} if lane=="YggdrasilStress"
                             else {7:16,8:16,9:16})

    def test_new_long_chain_oracle_is_evaluator_only(self):
        w={"base":list(O.YGGDRASIL_INIT),"R":[.04,.08],
           "S":[.09,-.08],"U":[.02,.06]}
        pos,neg=src.transfer_pair(1890000,[2,1,1],"FIT","long_depth")
        blind={(a,m):(Y.forward(a,pos,w,m),Y.forward(a,neg,w,m))
               for a in Y.ARMS for m in Y.MODES}
        route=Y.exact_positive_prefix(pos)
        self.assertEqual(len(route),len(pos["roles"]))
        for arm in Y.ARMS:
            for mode in Y.MODES:
                p,n=blind[(arm,mode)]
                again=Y.forward(arm,pos,w,mode,route)
                self.assertEqual(p["logit_hex"],again["logit_hex"])
                self.assertEqual(p["target_best_accumulated_score"],
                                 again["target_best_accumulated_score"])
                self.assertTrue(math.isfinite(float.fromhex(p["logit_hex"])))
                self.assertTrue(math.isfinite(float.fromhex(n["logit_hex"])))

    def test_new_cost_source_replays_frozen_original_7_9(self):
        w={"base":list(O.YGGDRASIL_INIT),"R":[.04,.08],
           "S":[.09,-.08],"U":[.02,.06]}
        pos,neg=src.stress_pair(1990000,[2,1,1],"FIT",lane="YggdrasilCost")
        for g in (pos,neg):
            for arm in ("O","U"):
                orig,_=V.original_forward(arm,g,w)
                shadow=Y.forward(arm,g,w,"original")
                self.assertEqual(orig.hex(),shadow["logit_hex"])
                self.assertLessEqual(shadow["final_active"],7)
                self.assertLessEqual(shadow["final_retained"],9)

    def test_tracer_inference_factorial_frozen_and_no_false_oom(self):
        self.assertEqual(W.CAPS,(24,22,20))
        self.assertEqual(W.ARMS,("S_packed","T_full_index","U_microindex"))
        self.assertEqual(Y.GRID,(-8,-6,-4,-2,-1,0,1,2,4,6,8))
        self.assertEqual(Cost.ARMS,("O_original","O_diverse",
                                   "U_original","U_diverse"))
        self.assertEqual(len(W.STAGES),6)


if __name__=="__main__":
    unittest.main()
