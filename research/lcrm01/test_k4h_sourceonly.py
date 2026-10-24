"""K4H source-free scientific safeguards; no CausalWorld import or source use."""
import json
import unittest
from types import SimpleNamespace
import numpy as np

from k4h_varied_worlds import (
    FROZEN,load_protocol,source_task,action,public_features,fit_models,
    predict,choose,observe_public_context,make_frozen_plan,paired_violations,
    evaluate_plan,verdict,METHODS,canonical)

def fixture(p,phases=("FIT",)):
    rows=[]
    for fam in p["world"]["families"]:
        for v in p["variants"]:
            if v["phase"] not in phases:continue
            x=[0.0]*128
            x[0]=v["goal_dx"];x[1]=v["goal_dy"]
            for arm in range(4):
                rows.append({"family":fam,"variant":v["id"],"phase":v["phase"],
                   "arm":arm,"reward":float(arm)+v["goal_dx"],"steps":8,
                   "initial_observation_sha256":"%s-%s"%(fam,v["id"]),
                   "action_sha256":"%s-%s"%(fam,arm),"features":x})
    return rows

class K4HAdversarial(unittest.TestCase):
    def test_exact_disjoint_source_configs(self):
        p=load_protocol()
        self.assertEqual(len(p["variants"]),7)
        self.assertEqual({v["id"] for v in p["variants"] if v["phase"]=="DEV"},{5,6})
        self.assertFalse(p["restriction"]["scientific_first_use"])

    def test_reaching_goal_parameters_physically_distinct(self):
        p=load_protocol()
        calls=[]
        def construct(**kw):calls.append(kw);return kw
        v=p["variants"][5]
        source_task(np,construct,p,"reaching",v)
        self.assertEqual(calls[0]["task_generator_id"],"reaching")
        self.assertAlmostEqual(calls[0]["default_goal_60"][0],0.03)
        self.assertAlmostEqual(calls[0]["default_goal_300"][2],0.16)

    def test_pushing_goal_and_tool_have_opposed_shifts(self):
        p=load_protocol();v=p["variants"][5]
        args=source_task(np,lambda **kw:kw,p,"pushing",v)
        self.assertAlmostEqual(args["tool_block_position"][0],-0.03)
        self.assertAlmostEqual(args["goal_block_position"][0],0.03)
        self.assertAlmostEqual(args["goal_block_position"][1],0.09)

    def test_actions_are_genuinely_distinct_and_in_bounds(self):
        space=SimpleNamespace(low=np.full(9,-1.0),high=np.full(9,1.0))
        actions=[action(np,space,i) for i in range(4)]
        self.assertEqual(len({x.tobytes() for x in actions}),4)
        with self.assertRaises(ValueError):action(np,space,4)

    def test_only_public_observation_reaches_predictor(self):
        self.assertEqual(len(public_features(np,[0.5,0.1,0.0])),128)
        with self.assertRaises(ValueError):public_features(np,[float("nan")])
        with self.assertRaises(ValueError):public_features(np,list(range(129)))

    def test_same_public_reset_per_action_required(self):
        p=load_protocol();rows=fixture(p)
        self.assertEqual(paired_violations(rows,[v for v in p["variants"] if v["phase"]=="FIT"],p),[])
        rows[1]["initial_observation_sha256"]="drift"
        self.assertEqual(paired_violations(rows,[v for v in p["variants"] if v["phase"]=="FIT"],p)[0]["reason"],"RESET_OBSERVATION_DRIFT")

    def test_each_conventional_model_fits_all_four_actions(self):
        p=load_protocol();s=fit_models(np,fixture(p),p)
        self.assertEqual(s["train_episode_count"],32)
        for fam in p["world"]["families"]:
            self.assertEqual(len(s["by_family"][fam]["records"]),4)
            self.assertEqual(len(s["by_family"][fam]["ridge"]["0"]),129)

    def test_missing_fit_source_denied(self):
        p=load_protocol()
        with self.assertRaises(ValueError):fit_models(np,fixture(p)[:-1],p)

    def test_state_serialization_preserves_choices(self):
        p=load_protocol();s=fit_models(np,fixture(p),p)
        loaded=json.loads(canonical(s));x=fixture(p)[0]["features"]
        self.assertEqual([(m,choose(np,s,"pushing",x,m)) for m in METHODS],
                         [(m,choose(np,loaded,"pushing",x,m)) for m in METHODS])

    def test_public_probes_must_precede_outcomes_and_match(self):
        p=load_protocol();s=fit_models(np,fixture(p),p)
        rows=fixture(p,("CHECK",))
        contexts=[{"family":rows[0]["family"],"variant":rows[0]["variant"],
                   "features":rows[0]["features"],
                   "initial_observation_sha256":rows[0]["initial_observation_sha256"]}]
        plan=make_frozen_plan(np,s,contexts,p)
        self.assertEqual(len(plan),1)
        self.assertEqual(len(evaluate_plan(rows[:4],plan)),1)
        rows[0]["initial_observation_sha256"]="forged"
        with self.assertRaises(ValueError):evaluate_plan(rows[:4],plan)

    def test_nondiscriminating_contexts_not_qualified(self):
        p=load_protocol();fit=fixture(p)
        dev_rows=fixture(p,("DEV",))
        for row in dev_rows:
            row["initial_observation_sha256"]="same"
        plan=[{"family":fam,"variant":v["id"],
               "public_observation_sha256":"same",
               "choices":{m:0 for m in METHODS}}
              for fam in p["world"]["families"] for v in p["variants"] if v["phase"]=="DEV"]
        scores=evaluate_plan(dev_rows,plan)
        d=verdict(fit,scores,dev_rows,[],p)
        self.assertEqual(d["source_variation"],"SOURCE_CONTEXT_NOT_QUALIFIED")
        self.assertEqual(d["contextual_generalization"],"CONTEXTUAL_GENERALIZATION_NOT_ESTABLISHED")
        self.assertFalse(d["scientific_accepted"])

    def test_change_action_is_not_context_learning(self):
        p=load_protocol()
        ft=fixture(p)
        dv=fixture(p,("DEV",))
        plan=[{"family":fam,"variant":v["id"],
               "public_observation_sha256":"%s-%s"%(fam,v["id"]),
               "choices":{m:1 for m in METHODS}}
              for fam in p["world"]["families"] for v in p["variants"] if v["phase"]=="DEV"]
        s=evaluate_plan(dv,plan)
        d=verdict(ft,s,dv,[],p)
        self.assertEqual(d["contextual_generalization"],"CONTEXTUAL_GENERALIZATION_NOT_ESTABLISHED")

if __name__=="__main__":
    unittest.main()
