"""K4U prospective native-fidelity and original-source guardrail tests.

No MiniGrid episodes are consumed in these source-only adversarial tests.
"""
import json
import unittest
from k4u_native_minigrid import (
    FROZEN,SCHEMA,METHODS,PHASE_SEEDS,protocol,source_hints,
    evaluate,public_grid,WingBridge)

def synthetic_outcomes():
    data=[]
    for family in ("empty","fourrooms"):
        for seed in PHASE_SEEDS["DEV"]:
            for method in METHODS:
                success=(method in ("wingless_native","yggdrasil_native",
                       "learned_model_bfs","public_bfs_expert","tabular_q"))
                data.append({"family":family,"seed":seed,"policy":method,
                    "success":success,"real_reward":0.8 if success else 0.0,
                    "first_action":seed%3})
    return data

class K4UOriginalSource(unittest.TestCase):
    def test_frozen_new_world_and_native_identity(self):
        p=protocol()
        self.assertEqual(tuple(PHASE_SEEDS["FIT"])[0],4100)
        self.assertEqual(tuple(PHASE_SEEDS["CHECK"])[-1],5103)
        self.assertEqual(tuple(PHASE_SEEDS["DEV"])[0],6100)
        self.assertEqual(p["sources"]["wingless"]["pr"],390)
        self.assertEqual(p["sources"]["yggdrasil"]["pr"],494)
        self.assertTrue(p["governance"]["no_FSA_writer"])

    def test_public_features_only_excludes_hidden_env(self):
        st={"x":4,"y":5,"goal":(6,7),"dir":2,
            "walls":frozenset(),"shape":(8,8),"grid_sha256":"abc"}
        k=public_grid(st)
        self.assertEqual(set(k),{"X","Y","GoalX","GoalY","Direction","FrontBlocked"})
        self.assertEqual(k["GoalX"],6)
        self.assertFalse(k["FrontBlocked"])

    def test_native_samples_need_fit_source_parity(self):
        from k4r_minigrid_source import FAMILIES
        initial=[{"family":f,"public_start_sha256":str(i)} for f in FAMILIES for i in range(24)]
        stream=[{"family":f,"action":a} for f in FAMILIES for a in range(3)]
        model={"FIT_source_eligible":True,"FIT_support":{"matches_public_documented_semantics":True}}
        self.assertTrue(source_hints(stream,initial,model)["qualified"])
        stream=[r for r in stream if not (r["family"]=="fourrooms" and r["action"]==2)]
        self.assertFalse(source_hints(stream,initial,model)["qualified"])

    def test_no_false_positive_if_conventional_equally_good(self):
        data=synthetic_outcomes()
        q=evaluate(data)
        self.assertEqual(q["result"],"NO_QUALIFIED_NATIVE_UNFAMILIAR_WORLD_TRANSFER")
        for fam in ("empty","fourrooms"):
            self.assertEqual(q["family_results"][fam]["success_rate"]["learned_model_bfs"],1.)
        self.assertFalse(q["scientific_accepted"])

    def test_positive_tests_require_both_independent_candidates(self):
        data=synthetic_outcomes()
        # Strong baselines intentionally fail on FourRooms for tabular Q;
        # requiring both native systems to qualify is the frozen primary.
        q=evaluate(data)
        self.assertFalse(q["per_candidate_frozen_gates"]["wingless_native"]["fourrooms_two_additional_wins_over_tabular_q"])
        native_bad=[r for r in data if r["family"]=="fourrooms"
                    and r["policy"]=="yggdrasil_native"]
        for r in native_bad:r["success"]=False;r["real_reward"]=0.
        self.assertEqual(evaluate(data)["result"],"NO_QUALIFIED_NATIVE_UNFAMILIAR_WORLD_TRANSFER")

    def test_cannot_abstain_or_treat_forward_as_illegal(self):
        p=protocol()
        self.assertEqual(p["worlds"]["legal_actions"],[0,1,2])
        self.assertIn("wingless_native",METHODS)
        self.assertIn("yggdrasil_native",METHODS)

if __name__=="__main__":
    unittest.main()
