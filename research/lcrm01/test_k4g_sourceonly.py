"""K4G predeclared action and control-competence checks (no simulator import)."""
import copy
import json
import unittest
from types import SimpleNamespace

import numpy as np

from k4g_action_identifiability import (
    frozen,action,trial,validate_paired_source,trained_means,
    select_policy,freeze_plan,score_phase,decision,MODES)

def synthetic_rows(p,seeds,variable=True):
    rows=[]
    for fam in p["world"]["families"]:
        for seed in seeds:
            for arm in range(4):
                rows.append({"family":fam,"seed":seed,"arm":arm,
                    "actual_public_return":float(arm) if variable else 0.0,
                    "step_count":8,"initial_observation_sha256":str(seed),
                    "legal_action_sha256":str(arm)})
    return rows

class FrozenK4GTests(unittest.TestCase):
    def test_frozen_unused_cohorts(self):
        p=frozen()
        all_seeds=p["world"]["new_fit_seeds"]+p["world"]["new_check_seeds"]+p["world"]["new_dev_seeds"]
        self.assertEqual(len(all_seeds),10)
        self.assertEqual(len(set(all_seeds)),10)
        self.assertFalse(p["research_restrictions"]["original_FSA_first_use"])

    def test_action_menu_strictly_legal_and_separate(self):
        space=SimpleNamespace(low=np.full(9,-2.),high=np.full(9,3.))
        a=[action(np,space,k) for k in range(4)]
        self.assertEqual(len({x.tobytes() for x in a}),4)
        self.assertTrue(np.all(a[0]==-2))
        self.assertTrue(np.all(a[1]==0.5))
        self.assertTrue(np.all(a[2]==3))
        self.assertEqual(float(a[3][0]),-1)
        self.assertEqual(float(a[3][1]),2)
        with self.assertRaises(ValueError):action(np,space,4)

    def test_degenerate_joint_space_fails(self):
        space=SimpleNamespace(low=np.ones(9),high=np.ones(9))
        with self.assertRaises(ValueError):action(np,space,0)

    def test_balanced_fit_data(self):
        p=frozen();fit=synthetic_rows(p,p["world"]["new_fit_seeds"])
        s=trained_means(fit,p)
        self.assertEqual(s["FIT_rows"],32)
        self.assertEqual(s["global_action_mean"]["3"],3)
        self.assertEqual(s["family_action_mean"]["pushing"]["3"],3)

    def test_missing_fit_arm_rejected(self):
        p=frozen();fit=synthetic_rows(p,p["world"]["new_fit_seeds"])
        with self.assertRaises(ValueError):trained_means(fit[:-1],p)

    def test_fitted_control_actions_frozen(self):
        p=frozen();fit=synthetic_rows(p,p["world"]["new_fit_seeds"])
        state=trained_means(fit,p)
        self.assertEqual(select_policy(state,"pushing",MODES[0]),0)
        self.assertEqual(select_policy(state,"pushing",MODES[1]),3)
        self.assertEqual(select_policy(state,"reaching",MODES[2]),3)
        self.assertEqual(len(freeze_plan(state,p["world"]["new_check_seeds"],p)),4)

    def test_source_initial_state_drift_denies_identifiability(self):
        p=frozen();rows=synthetic_rows(p,p["world"]["new_check_seeds"])
        rows[2]["initial_observation_sha256"]="BAD"
        errors=validate_paired_source(rows,p["world"]["new_check_seeds"],p)
        self.assertTrue(any(e["error"]=="PUBLIC_INITIAL_OBSERVATION_DRIFT" for e in errors))

    def test_causal_evidence_is_actual_reward_from_env(self):
        p=frozen()
        class Toy:
            def __init__(self,**kw):
                self.action_space=SimpleNamespace(low=np.full(9,-1.),high=np.full(9,1.))
                self.steps=0
            def reset(self):return np.array([1.,2.])
            def step(self,a):
                self.steps+=1
                return np.array([0.]),float(a[0]),False,{"forbidden_hidden_data":123}
            def close(self):pass
        r=trial(np,Toy,lambda task_generator_id:None,p,"reaching",503,2)
        self.assertEqual(r["step_count"],8)
        self.assertAlmostEqual(r["actual_public_return"],8.0)
        self.assertNotIn("forbidden_hidden_data",r)

    def test_non_discriminating_actions_veto(self):
        p=frozen();seeds=p["world"]["new_dev_seeds"]
        fit=synthetic_rows(p,p["world"]["new_fit_seeds"],variable=False)
        s=trained_means(fit,p)
        rows=synthetic_rows(p,seeds,variable=False)
        sc=score_phase(rows,freeze_plan(s,seeds,p))
        d=decision(sc,sc,[],p)
        self.assertEqual(d["disposition"],"BENCHMARK_NOT_QUALIFIED_RETAIN_NEGATIVE")

    def test_fitted_baseline_can_calibrate_bounded_public(self):
        p=frozen();seeds=p["world"]["new_dev_seeds"]
        state=trained_means(synthetic_rows(p,p["world"]["new_fit_seeds"]),p)
        sc=score_phase(synthetic_rows(p,seeds),freeze_plan(state,seeds,p))
        d=decision(sc,sc,[],p)
        self.assertEqual(d["disposition"],"CALIBRATED_PUBLIC_DEV_ONLY")
        self.assertFalse(d["scientific_accepted"])

    def test_matched_initial_drift_forces_negative(self):
        p=frozen();seeds=p["world"]["new_dev_seeds"]
        state=trained_means(synthetic_rows(p,p["world"]["new_fit_seeds"]),p)
        sc=score_phase(synthetic_rows(p,seeds),freeze_plan(state,seeds,p))
        d=decision(sc,sc,[{"error":"PUBLIC_INITIAL_OBSERVATION_DRIFT"}],p)
        self.assertEqual(d["disposition"],"BENCHMARK_NOT_QUALIFIED_RETAIN_NEGATIVE")

    def test_control_equals_fixed_never_claims_calibration(self):
        p=frozen();seeds=p["world"]["new_dev_seeds"]
        rows=synthetic_rows(p,seeds)
        plan=[{"family":fam,"seed":seed,"selected":{m:0 for m in MODES}}
             for fam in p["world"]["families"] for seed in seeds]
        d=decision(score_phase(rows,plan),score_phase(rows,plan),[],p)
        self.assertEqual(d["disposition"],"BENCHMARK_NOT_QUALIFIED_RETAIN_NEGATIVE")

if __name__=="__main__":
    unittest.main()
