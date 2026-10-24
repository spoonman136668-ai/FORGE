"""K4L prospective scientific/adversarial source-only qualification."""
import copy
import unittest
import numpy as np

from k4l_multicontext import (
    protocol, environment, decide, SCHEMA)
from k4k_compression import select_four, make_models, checkpoints, policy_choice, METHODS
from k4i_information_sufficiency import partition

def mock_fit():
    rows=[{"variant":i,"x":[i/12.0]+[0.0]*127,"y":float(i%4)}
          for i in range(12)]
    from copy import deepcopy
    return {"schema":"mass.k4i.conventional-trained-state.v1",
      "by_family":{fam:{"records":{str(arm):deepcopy(rows) for arm in range(4)},
              "mean":{str(arm):float(arm) for arm in range(4)},
              "ridge":{str(arm):[0.0]*129 for arm in range(4)},
              "feature_mean":[0.0]*128,"feature_scale":[1.0]*128}
              for fam in ("reaching","pushing")}}

def sample_decision(coverage_is_equal=False):
    scores=[]
    for fam in ("reaching","pushing"):
        for n in range(8):
            first=1 if n<4 else 3
            row={}
            for name in METHODS:
                if name=="family_mean":row[name]={"arm":1,"reward":0.0}
                elif name=="fixed_low":row[name]={"arm":0,"reward":-1.0}
                elif name in ("full_12","outcome_aware_4"):
                    row[name]={"arm":first,"reward":1.0 if n in (4,5,6) and fam=="reaching" else 0.0}
                elif name=="coverage_4":
                    row[name]={"arm":first if coverage_is_equal else 1,
                        "reward":1.0 if coverage_is_equal and n in (4,5,6) and fam=="reaching" else 0.0}
                else:row[name]={"arm":1,"reward":0.0}
            scores.append({"family":fam,"variant":14+n,
               "per_action_returns":{"0":-1.0,"1":0.0,"2":-1.0,"3":1.0 if n>=4 else -1.0},
               "selected":row})
    return scores

class K4LProtocolTests(unittest.TestCase):
    def test_frozen_new_world_cohorts(self):
        p=protocol();cfg,env=environment(p)
        self.assertEqual(len(p["cohort"]["variants"]),22)
        self.assertEqual(len(partition(cfg,"FIT")),12)
        self.assertEqual(len(partition(cfg,"CHECK")),2)
        self.assertEqual(len(partition(cfg,"DEV")),8)
        self.assertEqual(env["world"]["seed"],877)
        self.assertFalse(p["security"]["scientific_acceptance"])

    def test_original_k4k_four_exemplars_only(self):
        original=mock_fit()
        states=make_models(original)
        for mode in ("outcome_aware_4","coverage_4","uniform_4"):
            for family in ("reaching","pushing"):
                for arm in range(4):
                    self.assertEqual(len(states[mode]["by_family"][family]["records"][str(arm)]),4)
        self.assertEqual(len(states["full_12"]["by_family"]["reaching"]["records"]["0"]),12)

    def test_no_new_model_predictor(self):
        original=mock_fit();states=make_models(original)
        feature=[0.3]+[0.0]*127
        for model in METHODS:
            self.assertIn(policy_choice(np,states,original,"reaching",feature,model),range(4))

    def test_equal_capacity_coverage_veto(self):
        info={"reaching":{"best_arm_ids":[1,3]},"pushing":{"best_arm_ids":[1]}}
        sizes={"outcome_aware_4":40,"full_12":100}
        costs={"outcome_aware_4":{"CPU_ns":40},"full_12":{"CPU_ns":100}}
        out=decide(info,sample_decision(True),sizes,costs)
        self.assertEqual(out["result"],"K4L_NOT_QUALIFIED_PRESERVE_FULL_NEGATIVE")
        self.assertFalse(out["tests"]["beats_equal_capacity_coverage_by_0_01"])

    def test_positive_requires_every_prespecified_condition(self):
        info={"reaching":{"best_arm_ids":[1,3]},"pushing":{"best_arm_ids":[1]}}
        sizes={"outcome_aware_4":40,"full_12":100}
        costs={"outcome_aware_4":{"CPU_ns":40},"full_12":{"CPU_ns":100}}
        out=decide(info,sample_decision(),sizes,costs)
        self.assertEqual(out["result"],"K4L_BOUNDED_UNIQUE_CONTEXT_MEMORY_PARETO_POSITIVE")
        self.assertFalse(out["scientific_accepted"])
        self.assertEqual(out["per_family"]["reaching"]["strict_improved_vs_trained_constant"]["outcome_aware_4"],3)

    def test_insufficient_cpu_advantage_fails(self):
        info={"reaching":{"best_arm_ids":[1,3]},"pushing":{"best_arm_ids":[1]}}
        sizes={"outcome_aware_4":40,"full_12":100}
        costs={"outcome_aware_4":{"CPU_ns":75},"full_12":{"CPU_ns":100}}
        self.assertEqual(decide(info,sample_decision(),sizes,costs)["result"],
                         "K4L_NOT_QUALIFIED_PRESERVE_FULL_NEGATIVE")

    def test_one_context_improvement_fails(self):
        info={"reaching":{"best_arm_ids":[1,3]},"pushing":{"best_arm_ids":[1]}}
        sizes={"outcome_aware_4":40,"full_12":100}
        costs={"outcome_aware_4":{"CPU_ns":40},"full_12":{"CPU_ns":100}}
        rows=sample_decision()
        for r in rows:
            if r["family"]=="reaching" and r["variant"] in (19,20):
                r["selected"]["outcome_aware_4"]["reward"]=0.0
        self.assertEqual(decide(info,rows,sizes,costs)["result"],
                         "K4L_NOT_QUALIFIED_PRESERVE_FULL_NEGATIVE")

if __name__=="__main__":
    unittest.main()
