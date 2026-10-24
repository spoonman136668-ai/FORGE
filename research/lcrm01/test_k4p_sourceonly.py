"""K4P source-only safety, real learning, strong fitted control parity tests."""
import json
import unittest
from types import SimpleNamespace
import numpy as np

from k4p_predictive_state import (
    FROZEN,METHODS,CONTROLS,protocol,task,public,action,trained,
    predict,choose,freeze_plan,scoring,decision,canon,subset)

def fit_records():
    rows=[]
    for fam in ("reaching","pushing"):
        for i in range(12):
            x=[0.0]*128;x[0]=i/12;x[1]=.02 if fam=="reaching" else .04
            for arm in range(4):
                delta=[0.0]*128
                delta[0]=.15+arm*.015+i*.003
                delta[1]=.05*(arm%2)
                reward=float((arm-1)*.1+i*.03)
                rows.append({"family":fam,"variant":i,"arm":arm,
                    "x":x,"delta":delta,"reward":reward})
    return rows

class K4PSourceOnly(unittest.TestCase):
    def test_protocol_new_cohorts_three_families(self):
        p=protocol()
        self.assertEqual(len(subset(p,"FIT")),12)
        self.assertEqual(len(subset(p,"CHECK")),2)
        self.assertEqual(len(subset(p,"DEV")),8)
        self.assertEqual(p["cohort"]["unfamiliar_family"],"picking")
        self.assertFalse(p["governance"]["scientific_first_use"])

    def test_source_supported_public_task_parameters(self):
        p=protocol();v=subset(p,"DEV")[0]
        r=task(np,lambda **kw:kw,"reaching",v)
        self.assertAlmostEqual(r["default_goal_60"][0],v["goal_dx"])
        r=task(np,lambda **kw:kw,"picking",v)
        self.assertAlmostEqual(r["tool_block_position"][1],v["goal_dy"])
        self.assertNotIn("hidden_state",r)

    def test_original_legal_actions_and_invalid_bounds(self):
        space=SimpleNamespace(low=np.full(9,-1.),high=np.full(9,1.))
        acts=[action(np,space,a) for a in range(4)]
        self.assertEqual(len({a.tobytes() for a in acts}),4)
        with self.assertRaises(ValueError):
            action(np,space,4)

    def test_public_features_never_hidden_source(self):
        x=public(np,[0.1,0.2,0.3])
        self.assertEqual(x.shape,(128,))
        with self.assertRaises(ValueError):public(np,[float("nan")])
        with self.assertRaises(ValueError):public(np,list(range(129)))

    def test_transition_latent_training_not_constant(self):
        model=trained(np,fit_records())
        self.assertEqual(model["FIT_rows"],96)
        self.assertEqual(set(model["families"]),{"reaching","pushing"})
        arm=model["families"]["reaching"]["by_arm"]["1"]
        self.assertEqual(len(arm["transition"]),7)
        self.assertEqual(len(arm["head"]),11)
        self.assertEqual(len(arm["records"]),12)

    def test_missing_fit_is_denied(self):
        with self.assertRaises(ValueError):trained(np,fit_records()[:-1])

    def test_checkpoint_retention_preserves_every_prediction(self):
        model=trained(np,fit_records())
        restored=json.loads(canon(model))
        x=fit_records()[0]["x"]
        for method in METHODS:
            for arm in range(4):
                self.assertEqual(predict(np,model,"reaching",x,arm,method),
                                 predict(np,restored,"reaching",x,arm,method))

    def test_zero_shot_picking_uses_only_fit_families(self):
        model=trained(np,fit_records())
        x=fit_records()[0]["x"]
        for method in METHODS:
            self.assertIn(choose(np,model,"picking",x,method),range(4))
        self.assertNotIn("picking",model["families"])

    def test_heldout_plan_does_not_contain_reward(self):
        model=trained(np,fit_records())
        contexts=[{"family":"picking","variant":14,
                   "x":fit_records()[0]["x"],"initial_sha256":"a"}]
        plan=freeze_plan(np,model,contexts)
        self.assertEqual(set(plan[0]["choices"]),set(METHODS))
        self.assertNotIn("reward",canon(plan))

    def test_outcome_identity_drift_does_not_score(self):
        plan=[{"family":"reaching","variant":14,
            "public_observation_sha256":"true",
            "choices":{m:0 for m in METHODS}}]
        rows=[{"family":"reaching","variant":14,"arm":a,
               "start_sha256":"false","reward":float(a)} for a in range(4)]
        with self.assertRaises(ValueError):scoring(rows,plan)

    def test_science_veto_no_native_claim(self):
        scores=[]
        for fam in ("reaching","pushing","picking"):
            for i in range(8):
                scores.append({"family":fam,"variant":14+i,
                    "offline_best_action":1,
                    "selected":{m:{"arm":1,"reward":1.0} for m in METHODS}})
        d=decision(scores,None,{"reaching":{"fraction_MSE_reduction":0.2},
              "pushing":{"fraction_MSE_reduction":0.2}},
              {"predictive_state":5,"raw_1nn":100},
              {"predictive_state":{"cpu_ns":2},"raw_1nn":{"cpu_ns":100}})
        self.assertEqual(d["result"],"NO_QUALIFIED_PREDICTIVE_STATE_TRANSFER")
        self.assertFalse(d["scientific_accepted"])

if __name__=="__main__":
    unittest.main()
