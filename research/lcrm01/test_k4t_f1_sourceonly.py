"""K4T-F1 source-only falsifiers. Never run or import an original environment."""
import unittest
from k4t_f1_corrected_prospective import protocol,decide,FIT,CHECK,DEV,METHODS


def fake_metrics(goals_r1,goals_r2,blocked_r1,blocked_r2):
    return {f:{
        "wingless_r1":{"successes":goals_r1,"blocked_forward_per_100_steps":blocked_r1,
                       "mean_real_reward":0.1},
        "wingless_r2":{"successes":goals_r2,"blocked_forward_per_100_steps":blocked_r2,
                       "mean_real_reward":0.1 if goals_r2==0 else 0.9},
        "fit_dynamics_bfs":{"successes":8,"mean_real_reward":0.9}
    } for f in ("empty","fourrooms")}


class K4TF1FrozenSource(unittest.TestCase):
    def test_preregistration_and_fresh_cohorts(self):
        p=protocol()
        self.assertEqual(p["gate"],"LCRM01-K4T-F1")
        self.assertEqual(len(FIT),24)
        self.assertEqual(len(CHECK),4)
        self.assertEqual(len(DEV),8)
        self.assertFalse(set(FIT)&set(CHECK))
        self.assertFalse(set(FIT)&set(DEV))
        self.assertFalse(set(CHECK)&set(DEV))
        self.assertEqual(len(METHODS),9)
        self.assertFalse(p["governance"]["scientific_first_use"])
        self.assertFalse(p["governance"]["scientific_accepted"])

    def test_inhibition_without_actual_goals_is_no_go(self):
        q={"result":"COMPLETE_PROSPECTIVE_NATIVE_AFFORDANCE_EVALUATION",
           "source_science":{"results":fake_metrics(0,0,98.,0.)}}
        v=decide(q)
        self.assertEqual(v["result"],"NO_CORRECTED_WINGLESS_AFFORDANCE_TRANSFER_DEMONSTRATION")
        self.assertFalse(v["criteria"]["fourrooms_four_goals"])

    def test_true_goal_and_blocking_improvement_requires_full_parity(self):
        q={"result":"COMPLETE_PROSPECTIVE_NATIVE_AFFORDANCE_EVALUATION",
           "source_science":{"results":fake_metrics(0,6,95.,20.)}}
        v=decide(q)
        self.assertEqual(v["result"],
          "BOUNDED_CORRECTED_WINGLESS_AFFORDANCE_TRANSFER_DEVELOPMENT_ONLY_NOT_NOVELTY")
        self.assertFalse(v["scientific_accepted"])
        self.assertTrue(v["novelty_and_causal_ablation_not_qualified"])

    def test_failed_fit_does_not_claim_transfer(self):
        v=decide({"result":"FIT_SOURCE_NOT_QUALIFIED_HELDOUT_UNCONSUMED"})
        self.assertEqual(v["result"],"FIT_ORIGINAL_SOURCE_INELIGIBLE_NO_HELDOUT_ADVANCEMENT")
        self.assertFalse(v["scientific_accepted"])

    def test_no_rescue_with_incompetent_conventional_planner(self):
        m=fake_metrics(0,6,98.,0.)
        m["fourrooms"]["fit_dynamics_bfs"]["successes"]=5
        q={"result":"COMPLETE_PROSPECTIVE_NATIVE_AFFORDANCE_EVALUATION",
           "source_science":{"results":m}}
        self.assertEqual(decide(q)["result"],
          "NO_CORRECTED_WINGLESS_AFFORDANCE_TRANSFER_DEMONSTRATION")


if __name__=="__main__":
    unittest.main()
