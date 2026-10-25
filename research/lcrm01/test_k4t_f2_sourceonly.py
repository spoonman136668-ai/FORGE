"""K4T-F2 source-only scientific gate tests: no simulator or heldout imported."""
import unittest
from k4t_f2_r3_original_public import (
 contract, judgment, METHODS, FIT, CHECK, DEV, FAMILIES, R3_METHODS)

def sample(r3, r2, n, fitted=8):
 result={}
 for fam in FAMILIES:
  item={}
  for m in METHODS:
   goals=(r3 if m=="wingless_r3" else
          r2 if m=="wingless_r2" else
          n if m=="wingless_r3_no_plan" else
          fitted if m=="fit_dynamics_bfs" else 0)
   item[m]={"successes":goals,
            "mean_real_reward":0.0 if goals==0 else goals/8,
            "blocked_forward_per_100_steps":0.0,
            "actual_total_steps":80}
  result[fam]=item
 return result

class FrozenR3ScientificAdmission(unittest.TestCase):
 def test_new_source_identities_are_disjoint_and_fixed(self):
  p=contract()
  self.assertEqual(len(METHODS),11)
  self.assertEqual(p["cohorts"]["FIT"]["start"],41400)
  self.assertEqual(p["cohorts"]["DEV"]["start"],43400)
  self.assertEqual(len(FIT),24)
  self.assertEqual(len(CHECK),4)
  self.assertEqual(len(DEV),8)
  self.assertFalse(set(FIT)&set(CHECK))
  self.assertFalse(set(FIT)&set(DEV))
  self.assertFalse(set(CHECK)&set(DEV))
  self.assertEqual(len(R3_METHODS),2)
  self.assertFalse(p["first_use"])

 def test_no_goal_improvement_is_no_go(self):
  scores=sample(r3=2,r2=2,n=2)
  v=judgment({"results":scores},[{
   "family":fam,"method":method,
   "success":i<goals,"real_total_reward":1.0 if i<goals else 0.0,
   "actual_public_step_trace":[{"a":0,"before":[0,0,0,0,0,False]}]}
   for fam in FAMILIES
   for method in R3_METHODS
   for i in range(8)
   for goals in [scores[fam][method]["successes"]]])
  self.assertEqual(v["result"],"NO_R3_MODEL_NAVIGATION_ADVANCEMENT")
  self.assertFalse(v["criteria"]["two_real_additional_goals_over_r2"])

 def test_ablating_plan_must_reduce_real_goals(self):
  scores=sample(r3=6,r2=2,n=6)
  traces=[{"family":fam,"method":m,"success":i<6,
    "real_total_reward":1.0 if i<6 else 0.,
    "actual_public_step_trace":[{"a":0,"before":[0,0,0,0,0,False]}]}
    for fam in FAMILIES for m in R3_METHODS for i in range(8)]
  v=judgment({"results":scores},traces)
  self.assertFalse(v["criteria"]["empty_r3_goal_better_than_no_plan"])
  self.assertEqual(v["result"],"NO_R3_MODEL_NAVIGATION_ADVANCEMENT")

 def test_positive_gate_never_claims_scientific_acceptance(self):
  scores=sample(r3=6,r2=2,n=2)
  traces=[{"family":fam,"method":m,
   "success":i<(6 if m=="wingless_r3" else 2),
   "real_total_reward":1.0 if i<(6 if m=="wingless_r3" else 2) else 0.,
   "actual_public_step_trace":[{"a":0,"before":[0,0,0,0,0,False]}]}
   for fam in FAMILIES for m in R3_METHODS for i in range(8)]
  v=judgment({"results":scores},traces)
  self.assertEqual(v["result"],"BOUNDED_R3_ACTION_MODEL_GOAL_DEVELOPMENT_GAIN_NOT_NOVELTY")
  self.assertFalse(v["scientific_accepted"])
  self.assertTrue(v["not_proof_of_novel_native_causal_representation"])

if __name__=="__main__":unittest.main()
