"""K4N source-only FIT-fidelity memory, custody, and no false acceptance guards."""
import copy
import json
import unittest
import numpy as np
from k4n_decision_coreset import (
    FROZEN,METHODS,protocol,environment,fit_decision_fidelity,
    policy_choice,checkpoints,decide)
from k4k_compression import make_models
from k4i_information_sufficiency import partition

def training():
    rows=[]
    data={"schema":"mass.k4i.conventional-trained-state.v1","by_family":{}}
    for fam in ("reaching","pushing"):
        dataset={}
        for arm in range(4):
            data_rows=[]
            for vid in range(12):
                public=[vid/12,0.15 if fam=="pushing" else 0]+[0.0]*126
                reward=(10 if arm==(3 if vid>=6 else 1) else 0)+vid*0.01
                rows.append({"family":fam,"variant":vid,"arm":arm,
                    "features":public,"reward":float(reward)})
                data_rows.append({"variant":vid,"x":public,"y":float(reward)})
            dataset[str(arm)]=data_rows
        data["by_family"][fam]={"records":dataset,
            "mean":{str(a):1.0 for a in range(4)},
            "ridge":{str(a):[0.0]*129 for a in range(4)},
            "feature_mean":[0.0]*128,"feature_scale":[1.0]*128}
    return data,rows

def quality(coverage_equal=False,strict=3):
    score=[]
    for fam in ("reaching","pushing"):
        for i in range(8):
            good=fam=="reaching" and i>=8-strict
            method_rows={}
            for name in METHODS:
                if name=="family_mean":
                    method_rows[name]={"arm":1,"reward":0.0}
                elif name=="fit_fidelity_4":
                    method_rows[name]={"arm":3 if good else 1,"reward":1.0 if good else 0.0}
                elif name=="full_12":
                    method_rows[name]={"arm":3 if good else 1,"reward":1.0 if good else 0.0}
                elif name in ("coverage_4","outcome_aware_4"):
                    method_rows[name]={"arm":3 if coverage_equal and good else 1,
                         "reward":1.0 if coverage_equal and good else 0.0}
                else:
                    method_rows[name]={"arm":1,"reward":0.0}
            score.append({"family":fam,"variant":14+i,
                "per_action_returns":{"0":-1,"1":0,"2":-1,"3":1 if i%2 else -1},
                "selected":method_rows})
    return score

class K4NFrozenGuards(unittest.TestCase):
    def test_cohorts_and_no_scientific_authority(self):
        p=protocol()
        cfg,world=environment(p)
        self.assertEqual(len(p["cohort"]["variants"]),22)
        self.assertEqual(len(partition(cfg,"FIT")),12)
        self.assertEqual(len(partition(cfg,"DEV")),8)
        self.assertEqual(world["world"]["seed"],907)
        self.assertFalse(p["governance"]["scientific_accepted"])

    def test_same_original_capacity_and_no_training_mutation(self):
        state,rows=training()
        prior=copy.deepcopy(state)
        models=make_models(state)
        fitted,audit=fit_decision_fidelity(np,state,models,rows,protocol())
        self.assertEqual(state,prior)
        self.assertEqual(len(audit),2)
        for fam in ("reaching","pushing"):
            for arm in range(4):
                chosen=fitted["by_family"][fam]["records"][str(arm)]
                self.assertEqual(len(chosen),4)
                self.assertEqual(len(set(r["variant"] for r in chosen)),4)
                self.assertTrue(all(r in prior["by_family"][fam]["records"][str(arm)]
                                    for r in chosen))
            self.assertLessEqual(len(audit[fam]["strict_improving_swaps"]),8)
            self.assertLessEqual(audit[fam]["final_FIT_loss"],audit[fam]["initial_FIT_loss"])
        self.assertEqual(len(models["full_12"]["by_family"]["reaching"]["records"]["0"]),12)

    def test_only_public_source_actions_and_unmodified_nearest_predictor(self):
        state,rows=training()
        models=make_models(state)
        model,_=fit_decision_fidelity(np,state,models,rows,protocol())
        models["fit_fidelity_4"]=model
        x=[0.2,0.0]+[0.0]*126
        self.assertIn(policy_choice(np,models,state,"reaching",x,"fit_fidelity_4"),range(4))
        self.assertIn(policy_choice(np,models,state,"reaching",x,"coverage_4"),range(4))
        self.assertLess(checkpoints(models,state)["fit_fidelity_4"],
                        checkpoints(models,state)["full_12"])

    def test_positive_requires_unique_quality_resource_and_diverse_real_actions(self):
        info={"reaching":{"best_arm_ids":[1,3]},"pushing":{"best_arm_ids":[1]}}
        sizes={"fit_fidelity_4":40,"full_12":100}
        timing={"fit_fidelity_4":{"CPU_ns":40},"full_12":{"CPU_ns":100}}
        q=decide(info,quality(),sizes,timing)
        self.assertEqual(q["result"],"K4N_BOUNDED_NEW_SOURCE_DECISION_CORESET_POSITIVE")
        self.assertFalse(q["scientific_accepted"])

    def test_equal_capacity_coverage_cannot_claim_unique_improvement(self):
        info={"reaching":{"best_arm_ids":[1,3]},"pushing":{"best_arm_ids":[1]}}
        sizes={"fit_fidelity_4":40,"full_12":100}
        timing={"fit_fidelity_4":{"CPU_ns":40},"full_12":{"CPU_ns":100}}
        q=decide(info,quality(coverage_equal=True),sizes,timing)
        self.assertEqual(q["result"],"K4N_NO_QUALIFIED_UNIQUE_MEMORY_ADVANCEMENT")

    def test_two_case_success_not_enough(self):
        info={"reaching":{"best_arm_ids":[1,3]},"pushing":{"best_arm_ids":[1]}}
        sizes={"fit_fidelity_4":40,"full_12":100}
        timing={"fit_fidelity_4":{"CPU_ns":40},"full_12":{"CPU_ns":100}}
        q=decide(info,quality(strict=2),sizes,timing)
        self.assertFalse(q["requirements"]["at_least_3_of_8_strict_better_cases"])

    def test_cpu_regression_denies_quality_positive(self):
        info={"reaching":{"best_arm_ids":[1,3]},"pushing":{"best_arm_ids":[1]}}
        sizes={"fit_fidelity_4":40,"full_12":100}
        timing={"fit_fidelity_4":{"CPU_ns":90},"full_12":{"CPU_ns":100}}
        q=decide(info,quality(),sizes,timing)
        self.assertEqual(q["result"],"K4N_NO_QUALIFIED_UNIQUE_MEMORY_ADVANCEMENT")

if __name__=="__main__":
    unittest.main()
