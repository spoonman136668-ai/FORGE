"""K4Q adversarial public-source causality and FIT-first qualification."""
import json
import unittest
from types import SimpleNamespace
import numpy as np
from k4q_causal_observability import (
    FROZEN,frozen,cohort,initial_joint_positions,observe,check_fit,
    learn,predictor,plan,score,summarize,verdict,METHODS,FAMILIES,canon)

def fake_fit(nonvarying=False):
    rows=[]
    for fam in FAMILIES:
        for v in range(12):
            x=[0.0]*128;x[0]=v/12.;x[1]=.5 if fam=="pushing" else .3 if fam=="picking" else 0
            for arm in range(4):
                d=[0.0]*128
                d[0]=.1*arm+ (0 if nonvarying else v*.02)
                d[1]=.03*arm+ (0 if nonvarying else v*.01)
                rows.append({"family":fam,"variant":v,"arm":arm,
                  "reset_sha256":str(fam)+":"+str(v),
                  "action_sha256":str(arm),
                  "delta_sha256":str((fam,arm,v if not nonvarying else 0)),
                  "x":x,"delta":d,"reward":float(arm+(1 if v>5 else -1)*(arm-2)*2),
                  "steps":8})
    return rows

class K4QOriginalSourceTests(unittest.TestCase):
    def test_frozen_public_intervention_and_unique_task_sources(self):
        p=frozen()
        self.assertEqual(len(cohort(p,"FIT")),12)
        self.assertEqual(len(cohort(p,"CHECK")),2)
        self.assertEqual(len(cohort(p,"DEV")),4)
        self.assertEqual(p["source_design"]["phases"],{"FIT":144,"CHECK":24,"DEV":48})
        self.assertFalse(p["qualify"]["governance"]["scientific_first_use"])

    def test_initial_robot_joints_are_nontrivial_and_bounded(self):
        p=frozen()
        a=initial_joint_positions(np,cohort(p,"FIT")[0])
        b=initial_joint_positions(np,cohort(p,"FIT")[11])
        self.assertEqual(a.shape,(9,))
        self.assertGreater(float(np.sum((a-b)**2)),1e-4)
        self.assertTrue(np.all(a > -3.) and np.all(a < 3.))

    def test_public_intervention_failure_is_not_silent(self):
        class Stub:
            def set_starting_state(self,values,check_bounds):
                return False,np.zeros(10)
        with self.assertRaises(ValueError):
            observe(np,Stub(),cohort(frozen(),"FIT")[0])

    def test_actual_public_intervention_success_is_consumed(self):
        class Stub:
            def set_starting_state(self,values,check_bounds):
                assert "joint_positions" in values and check_bounds
                return True,np.arange(10,dtype=np.float64)
        x=observe(np,Stub(),cohort(frozen(),"FIT")[0])
        self.assertEqual(len(x),10)

    def test_fit_qualification_uses_true_causal_transitions(self):
        p=frozen()
        info,eligible=check_fit(np,fake_fit(),p)
        self.assertTrue(eligible)
        self.assertTrue(all(info[f]["state_transitions_variable"] for f in FAMILIES))
        self.assertEqual(len(info["reaching"]["FIT_best_action_ids"]),2)

    def test_constant_action_transition_veto(self):
        p=frozen()
        info,eligible=check_fit(np,fake_fit(True),p)
        self.assertFalse(eligible)
        self.assertFalse(info["reaching"]["state_transitions_variable"])

    def test_conventional_forward_models_use_only_equal_fit(self):
        model=learn(np,fake_fit())
        self.assertEqual(model["original_FIT_experiences"],144)
        self.assertEqual(set(model["by_family"]),set(FAMILIES))
        for fam in FAMILIES:
            for arm in range(4):
                self.assertEqual(len(model["by_family"][fam][str(arm)]["records"]),12)
                self.assertEqual(len(model["by_family"][fam][str(arm)]["ridge"]),(129))
        with self.assertRaises(ValueError):learn(np,fake_fit()[:-1])

    def test_frozen_predictions_reproducible_after_json(self):
        model=learn(np,fake_fit())
        rebuilt=json.loads(canon(model))
        x=fake_fit()[0]["x"]
        for method in METHODS:
            self.assertTrue(np.array_equal(
                predictor(np,model,"reaching",0,x,method),
                predictor(np,rebuilt,"reaching",0,x,method)))

    def test_reset_identity_cannot_change_at_scoring(self):
        model=learn(np,fake_fit())
        c={"family":"reaching","variant":12,"x":fake_fit()[0]["x"],
           "reset_sha256":"approved"}
        frozen_plan=plan(np,model,[c])
        actual=[{"family":"reaching","variant":12,"arm":arm,
                 "reset_sha256":"forged","delta":[0.0]*128,"reward":0.0}
                 for arm in range(4)]
        with self.assertRaises(ValueError):score(np,actual,frozen_plan)

    def test_predeclared_model_gate_not_cognitive_acceptance(self):
        one={f:{"best_fitted_MSE_reduction":.10,
              "distinct_hindsight_best_arms":2} for f in FAMILIES}
        result=verdict(one,one)
        self.assertEqual(result["result"],"SOURCE_OBSERVABILITY_AND_BASELINE_LEARNABILITY_QUALIFIED")
        self.assertFalse(result["science_accepted"])
        bad={f:dict(v) for f,v in one.items()}
        bad["reaching"]["best_fitted_MSE_reduction"]=0
        bad["pushing"]["best_fitted_MSE_reduction"]=0
        self.assertEqual(verdict(bad,bad)["result"],
           "SOURCE_INFORMATION_OR_BASELINE_LEARNABILITY_NOT_QUALIFIED")

if __name__=="__main__":
    unittest.main()
