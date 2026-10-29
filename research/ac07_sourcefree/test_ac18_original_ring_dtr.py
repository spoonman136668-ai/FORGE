"""AC-18 contract guards. Test fixtures below do not generate source science."""
import unittest
import ac18_original_ring_dtr as x

def fake(seed,s0,s1,a0,a1,reward):
    return {"seed":seed,"events":[
        {"stage":0,"observation":s0,"action":a0,"next_observation":s1,
         "reward":0,"terminated":False,"truncated":False,"valid_actions":[0,1]},
        {"stage":1,"observation":s1,"action":a1,"next_observation":None,
         "reward":reward,"terminated":True,"truncated":False,"valid_actions":[0,1]}
    ]}

class AC18Tests(unittest.TestCase):
    def test_pins_original_historical_source_and_current_not_equated(self):
        self.assertEqual(x.YGG_COMMIT,"a39171a76d0d7817e3563682bb139a9d7ecf37c4")
        self.assertEqual(x.RING_BLOB,"1db0835d5c99456bcf99a013d4836f49314a9d39")
        self.assertEqual(x.BRIDGE_BLOB,"b311ea7ea00c15d23e7bd43ff97bd10ce3d8b87c")
        self.assertNotEqual(x.YGG_COMMIT,x.CURRENT_ACTIVE_YGG)
        self.assertEqual(x.A_B_A,(760000,760001,760004))

    def test_stage_and_action_projection_never_fabricates_source_outcomes(self):
        a=fake(1,0,1,0,1,1)
        self.assertEqual([x.obs_name(e) for e in a["events"]],["LRV","docked_LRV"])
        self.assertEqual([x.action_name(e) for e in a["events"]],["TurnAround","GoForward"])
        self.assertEqual(x.episode_context(a),(0,1,1))
        self.assertNotIn("Backup",x.ACTIONS)

    def test_fitted_controls_ignore_dev_labels(self):
        fit=[fake(1,0,1,0,0,1),fake(2,0,1,0,0,0)]
        dev0=[fake(3,0,1,0,0,0)]
        dev1=[fake(3,0,1,0,0,1)]
        p0=x.same_information_controls(fit,dev0)
        p1=x.same_information_controls(fit,dev1)
        self.assertEqual(p0[0]["fitted_tabular_probability"],
                         p1[0]["fitted_tabular_probability"])
        self.assertEqual(p0[0]["fitted_acting_ema_probability"],
                         p1[0]["fitted_acting_ema_probability"])
        self.assertAlmostEqual(p0[0]["fitted_tabular_probability"],.5)

    def test_unsupported_history_falls_back_to_fitted_pooled_reward(self):
        fit=[fake(1,0,1,0,0,1),fake(2,0,1,0,0,0)]
        dev=[fake(3,1,0,1,1,1)]
        r=x.same_information_controls(fit,dev)[0]
        self.assertEqual(r["fit_context_support"],0)
        self.assertEqual(r["fitted_acting_ema_probability"],.5)
        self.assertEqual(r["fitted_tabular_probability"],.5)

    def test_same_information_accuracy_and_brier_are_separate(self):
        r=x.score([.2,.8],[0,1])
        self.assertEqual(r["correct_at_half"],2)
        self.assertAlmostEqual(r["brier"],.04)

    def test_source_parent_is_not_a_fixture(self):
        with self.assertRaisesRegex(RuntimeError,"PARENT_REAL_ORIGINAL_SOURCE"):
            x.exact_source({})
        self.assertTrue(set(x.ac15.FIT).isdisjoint(x.ac15.DEV))

    def test_reward_collision_means_same_local_features_not_source_causal_fact(self):
        rec={"local_action_features":[1.,.25,.5],
             "source_reward":0,"stage":1,"source_action":0,"public_obs":1}
        other=dict(rec,source_reward=1)
        data=[{"seed":760000,"records":[rec]},
              {"seed":760004,"records":[other]}]
        c=x.local_collisions(data)
        self.assertEqual(c["groups_with_source_reward_conflict"],1)
        self.assertTrue(c["no_proof_of_global_original_causal_nonidentifiability"])

    def test_genuine_full_native_bridge_incompatibility_is_not_relabelled(self):
        self.assertEqual(x.SCHEMA,"forge.ac18.authentic-dtr-historical-eight-cell-dev.v1")
        self.assertEqual(x.ACTIONS,("TurnAround","GoForward"))
        self.assertEqual(x.OBS1,("docked_MRV","docked_LRV"))

if __name__=="__main__":
    unittest.main()
