"""K4F frozen actual-learning, information parity and no-acceptance tests."""
import copy
import json
import math
import unittest
from types import SimpleNamespace

import numpy as np

from k4f_interactive_learning import (
    FROZEN,read_protocol,features,action_for,fit_models,predict,choose,
    decision,simulate,METHODS,SCHEMA,canon)

def fixtures():
    p=read_protocol()
    a=[]
    for i in range(32):
        arm=i%4
        a.append({"x":[float(i%8)/8]*15,"choice":arm,
                  "total_return":(arm-1)*0.05+float(i//4)*0.001})
    return p,a

def eval_rows(vals):
    return [{"task":"picking","seed":i,"method":m,"total_return":vals[m]}
            for i in (1,2,3,4) for m in METHODS]

class K4FSourceOnlyTests(unittest.TestCase):
    def test_preregistered_disjoint_source_cohorts(self):
        p=read_protocol(); c=p["cohorts"]
        chunks=[c["fit_seeds"],c["check_seeds"],c["unfamiliar_dev_seeds"],c["same_family_dev_seeds"]]
        self.assertEqual(len(set(sum(chunks,[]))),sum(map(len,chunks)))
        self.assertEqual(p["world"]["task_unfamiliar"],["picking"])
        self.assertFalse(p["safety"]["scientific_first_use"])

    def test_public_features_only_and_stable_length(self):
        self.assertEqual(len(features(np,np.arange(4,dtype=float))),15)
        self.assertEqual(len(features(np,np.arange(17,dtype=float))),15)
        with self.assertRaises(ValueError):
            features(np,np.array([math.nan]))

    def test_frozen_actions_and_bounds(self):
        p,_=fixtures()
        env=SimpleNamespace(low=np.full(9,-1.0),high=np.full(9,1.0))
        self.assertEqual(float(action_for(np,env,3,p)[0]),-0.96)
        self.assertEqual(float(action_for(np,env,3,p)[2]),-0.97)
        with self.assertRaises(ValueError):
            action_for(np,env,4,p)

    def test_action_bounds_fail_closed(self):
        p,_=fixtures()
        env=SimpleNamespace(low=np.full(9,1.0),high=np.full(9,1.01))
        with self.assertRaises(ValueError):
            action_for(np,env,3,p)

    def test_all_conventional_arms_fully_fit(self):
        p,a=fixtures();state=fit_models(np,a,p)
        self.assertEqual(state["counts"],[8]*4)
        self.assertEqual(state["training_experiences"],32)
        self.assertEqual(len(state["ridge"]),64)
        self.assertLessEqual(len(state["fast"]),16)

    def test_missing_equal_fit_data_denied(self):
        p,a=fixtures()
        with self.assertRaises(ValueError):
            fit_models(np,a[:-1],p)

    def test_retention_survives_serialization(self):
        p,a=fixtures();s=fit_models(np,a,p)
        restored=json.loads(canon(s))
        for m in METHODS:
            for choice in range(4):
                self.assertEqual(predict(np,s,a[0]["x"],choice,p,m),
                                 predict(np,restored,a[0]["x"],choice,p,m))

    def test_genuine_fitted_state_changes_from_zero(self):
        p,a=fixtures();s=fit_models(np,a,p)
        self.assertNotEqual(s["means"],[0.0]*4)
        self.assertNotEqual(s["ridge"],[0.0]*64)

    def test_five_methods_use_frozen_tie_break(self):
        p,a=fixtures();s=fit_models(np,a,p)
        self.assertEqual(choose(np,s,a[0]["x"],p,"fixed"),0)
        self.assertIn(choose(np,s,a[0]["x"],p,"ridge"),range(4))
        with self.assertRaises(ValueError):
            choose(np,s,a[0]["x"],p,"future_oracle")

    def test_ineligible_learner_cannot_claim_transfer(self):
        p,_=fixtures()
        worst={"selective_memory":0.0,"ridge":1.0,"knn":0.9,"mean":0.8,"fixed":0}
        r=decision(eval_rows(worst),eval_rows(worst),eval_rows(worst),p)
        self.assertEqual(r["decision"],"NO_EVIDENCE_OF_SUPERIOR_UNFAMILIAR_TRANSFER")

    def test_high_unfamiliar_gain_must_preserve_check(self):
        p,_=fixtures()
        good={"selective_memory":1.0,"ridge":0.5,"knn":0.6,"mean":0.4,"fixed":0.0}
        veto={"selective_memory":0.0,"ridge":1.0,"knn":0.7,"mean":0.6,"fixed":0.0}
        r=decision(eval_rows(veto),eval_rows(good),eval_rows(good),p)
        self.assertEqual(r["decision"],"NO_EVIDENCE_OF_SUPERIOR_UNFAMILIAR_TRANSFER")

    def test_positive_screen_never_scientific_admission(self):
        p,_=fixtures()
        good={"selective_memory":1.0,"ridge":0.5,"knn":0.6,"mean":0.4,"fixed":0}
        d=decision(eval_rows(good),eval_rows(good),eval_rows(good),p)
        self.assertEqual(d["decision"],"BOUNDED_DEV_TRANSFER_CANDIDATE")
        self.assertFalse(d["scientific_acceptance"])
        self.assertFalse(d["native_transfer_claim"])

    def test_simulate_collects_actual_public_reward_only(self):
        p,_=fixtures()
        class MockWorld:
            def __init__(self,**kw):
                self.action_space=SimpleNamespace(low=np.full(9,-1.),high=np.full(9,1.))
                self.steps=0
            def reset(self):
                return np.array([1.,2.,3.])
            def step(self,action):
                self.steps+=1
                return np.array([0.]),float(action[0]),False,{"private":"IGNORED"}
            def close(self):
                pass
        sample=simulate(np,MockWorld,lambda task_generator_id:None,p,"reaching",101,lambda x:1)
        self.assertEqual(sample["choice"],1)
        self.assertEqual(sample["reward_steps"],3)
        self.assertAlmostEqual(sample["total_return"],-2.88)
        self.assertEqual(len(sample["x"]),15)

    def test_non_public_unknown_task_denied(self):
        p,_=fixtures()
        with self.assertRaises(ValueError):
            simulate(np,object,lambda task_generator_id:None,p,"secret_holdout",1,lambda x:0)

if __name__=="__main__":
    unittest.main()
