"""F3 source-only prereg / original-controls falsification, no world imports."""
import unittest
from k4t_f3_original_r4_frontier import contract,FIT,CHECK,DEV,METHODS,FAMILIES,outcome

def original(r3,planner=8):
 return {"results":{
  f:{
   "wingless_r3":{"successes":r3,"mean_real_reward":r3/8,
     "blocked_forward_per_100_steps":0.0},
   "fit_dynamics_bfs":{"successes":planner,"mean_real_reward":planner/8,
     "blocked_forward_per_100_steps":0.0}
  } for f in FAMILIES}}

def traces(empty,fourrooms):
 return [{"family":family,"seed":seed,
   "method":"wingless_r4_frontier","success":i<n,
   "real_total_reward":float(i<n),
   "actual_public_step_trace":[{"a":0,"before":[0,0,0,0,0,0]}]}
   for family,n in (("empty",empty),("fourrooms",fourrooms))
   for i,seed in enumerate(DEV)]

class NativeR4Falsifiers(unittest.TestCase):
 def test_frozen_identity_and_fresh_disjoint_cohorts(self):
  c=contract()
  self.assertEqual(len(METHODS),12)
  self.assertEqual((len(FIT),len(CHECK),len(DEV)),(24,4,8))
  self.assertFalse(set(FIT)&set(CHECK))
  self.assertFalse(set(DEV)&set(CHECK))
  self.assertFalse(set(FIT)&set(DEV))
  self.assertFalse(set(DEV)&set(range(43400,43408)))
  self.assertFalse(c["scientific_first_use"])
  self.assertEqual(c["cohorts"]["shared_fit_events"],12000)
 def test_same_model_r3_without_frontier_is_strong_control(self):
  v=outcome(original(2),traces(8,2))
  self.assertFalse(v["criteria"]["fourrooms_two_extra_goals_over_r3"])
  self.assertEqual(v["result"],"NO_R4_FRONTIER_UNFAMILIAR_NAVIGATION_ADVANCEMENT")
 def test_frontier_alone_does_not_replace_original_real_goal(self):
  v=outcome(original(2),traces(2,0))
  self.assertFalse(v["criteria"]["fourrooms_goal_preserve"])
  self.assertFalse(v["scientific_accepted"])
 def test_comparable_true_gain_not_scientific_acceptance(self):
  v=outcome(original(2),traces(8,8))
  self.assertEqual(v["result"],"BOUNDED_R4_FRONTIER_SOURCE_DEV_ADVANCEMENT_NOT_NOVELTY")
  self.assertFalse(v["scientific_first_use"])
  self.assertFalse(v["information_parity_with_full_grid_planner"])
if __name__=="__main__":unittest.main()
