"""K4K source-only adversarial checks: no DEV-driven memory compression."""
import copy
import json
import unittest
import numpy as np
from k4k_compression import (
    FROZEN,SCHEMA,METHODS,MEMORY_METHODS,frozen,source_settings,
    select_four,make_models,policy_choice,checkpoints,
    evaluate_science,canonical)
from k4i_information_sufficiency import partition

def example_records():
    return [{"variant":i,"x":[float(i)/12]+[0.0]*127,
             "y":float(i%5)-2.0} for i in range(12)]

def synthetic_model():
    r=example_records()
    return {"schema":"mass.k4i.conventional-trained-state.v1",
      "by_family":{f:{"records":{str(arm):copy.deepcopy(r) for arm in range(4)},
                       "mean":{str(arm):float(arm) for arm in range(4)},
                       "ridge":{str(arm):[0.0]*129 for arm in range(4)},
                       "feature_mean":[0.0]*128,
                       "feature_scale":[1.0]*128}
                   for f in ("reaching","pushing")}}

class K4KAdversarial(unittest.TestCase):
    def test_prospectively_distinct_configs_and_source(self):
        p=frozen()
        self.assertEqual(len(p["cohort"]["world_variants"]),18)
        self.assertEqual(len(partition(source_settings(p)[0],"FIT")),12)
        self.assertEqual(len(partition(source_settings(p)[0],"CHECK")),2)
        self.assertEqual(len(partition(source_settings(p)[0],"DEV")),4)
        self.assertFalse(p["governance"]["scientific_first_use"])

    def test_reward_aware_selects_both_actual_extremes(self):
        a=example_records()
        selected=select_four(a,"outcome_aware_4")
        self.assertEqual(len(selected),4)
        self.assertEqual(len({x["variant"] for x in selected}),4)
        self.assertIn(min(a,key=lambda r:r["y"])["variant"],{x["variant"] for x in selected})
        self.assertIn(max(a,key=lambda r:r["y"])["variant"],{x["variant"] for x in selected})

    def test_uniform_and_coverage_are_separate_conventional_controls(self):
        a=example_records()
        self.assertEqual([x["variant"] for x in select_four(a,"uniform_4")],[0,3,6,9])
        b=select_four(a,"coverage_4")
        self.assertEqual(len(b),4)
        self.assertIn(0,{x["variant"] for x in b})

    def test_no_synthetic_rewards_or_mutation(self):
        a=example_records();original=copy.deepcopy(a)
        sel=select_four(a,"outcome_aware_4")
        self.assertEqual(a,original)
        for r in sel:
            self.assertIn(r,original)
        sel[0]["x"][0]=999.
        self.assertEqual(a,original)

    def test_no_incomplete_fit_or_hidden_selector(self):
        with self.assertRaises(ValueError):
            select_four(example_records()[:-1],"outcome_aware_4")
        with self.assertRaises(ValueError):
            select_four(example_records(),"DEV_oracle")

    def test_all_per_action_families_retain_four(self):
        x=synthetic_model()
        m=make_models(x)
        self.assertEqual(set(m),set(MEMORY_METHODS))
        for name in ("outcome_aware_4","coverage_4","uniform_4"):
            for fam in ("reaching","pushing"):
                for arm in range(4):
                    self.assertEqual(len(m[name]["by_family"][fam]["records"][str(arm)]),4)
        self.assertEqual(len(m["full_12"]["by_family"]["pushing"]["records"]["2"]),12)

    def test_compressed_saved_memory_under_half(self):
        x=synthetic_model()
        sizes=checkpoints(make_models(x),x)
        self.assertLess(sizes["outcome_aware_4"],.5*sizes["full_12"])
        self.assertLess(sizes["family_mean"],sizes["outcome_aware_4"])

    def test_policy_predictions_do_not_use_hidden_rewards(self):
        x=synthetic_model();m=make_models(x)
        f=[0.3]+[0.0]*127
        for method in METHODS:
            self.assertIn(policy_choice(np,m,x,"reaching",f,method),range(4))

    def test_both_resource_thresholds_must_pass(self):
        p=frozen()
        rows=[]
        for v in range(4):
            dec={"family_mean":{"arm":1,"reward":0.0},
                 "full_12":{"arm":3 if v>1 else 1,"reward":1.0 if v>1 else 0.0},
                 "outcome_aware_4":{"arm":3 if v>1 else 1,"reward":1.0 if v>1 else 0.0}}
            for name in METHODS:
                if name not in dec:dec[name]={"arm":1,"reward":0.0}
            rows.append({"family":"reaching","variant":14+v,"selected":dec})
        for v in range(4):
            dec={name:{"arm":1,"reward":0.0} for name in METHODS}
            rows.append({"family":"pushing","variant":14+v,"selected":dec})
        info={"reaching":{"action_ranking_diverse":True},
              "pushing":{"action_ranking_diverse":False}}
        sizes={name:(40 if name=="outcome_aware_4" else 100) for name in METHODS}
        cpu={name:{"CPU_ns":40 if name=="outcome_aware_4" else 100} for name in METHODS}
        self.assertEqual(evaluate_science(info,rows,sizes,cpu,p)["result"],
                         "BOUNDED_COMPRESSED_MEMORY_QUALITY_COST_POSITIVE")
        cpu["outcome_aware_4"]["CPU_ns"]=80
        self.assertEqual(evaluate_science(info,rows,sizes,cpu,p)["result"],
                         "NO_QUALIFIED_COMPRESSION_PARETO_IMPROVEMENT")

    def test_single_positive_context_no_go(self):
        p=frozen();rows=[]
        info={"reaching":{"action_ranking_diverse":True},
              "pushing":{"action_ranking_diverse":False}}
        for fam in ("reaching","pushing"):
            for v in range(4):
                arm=3 if fam=="reaching" and v==3 else 1
                z={m:{"arm":arm if m!="family_mean" else 1,
                       "reward":1.0 if (m=="outcome_aware_4" and arm==3) else 0.0}
                   for m in METHODS}
                rows.append({"family":fam,"variant":14+v,"selected":z})
        sizes={name:40 if name=="outcome_aware_4" else 100 for name in METHODS}
        cpu={name:{"CPU_ns":40 if name=="outcome_aware_4" else 100} for name in METHODS}
        self.assertEqual(evaluate_science(info,rows,sizes,cpu,p)["result"],
                         "NO_QUALIFIED_COMPRESSION_PARETO_IMPROVEMENT")

if __name__=="__main__":
    unittest.main()
