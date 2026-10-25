"""F5 frozen real-world empirical-route falsifiers; no source simulator run."""
import unittest
from k4t_f5_original_r6_edges import contract,FIT,CHECK,DEV,METHODS,FAMILIES,outcome

def fixtures(r5,r6,six=8,planner=8,r6reward=None):
 original={"results":{family:{"fit_dynamics_bfs":{
  "successes":planner,"mean_real_reward":planner/8,
  "blocked_forward_per_100_steps":0.0}} for family in FAMILIES}}
 dev=[]
 for fam in FAMILIES:
  for method,goals in (("wingless_r4_frontier",6),
                       ("wingless_r5_cost_frontier",r5),
                       ("wingless_r6_observed_route",r6),
                       ("sixfield_fit_model_route",six)):
   for j in range(8):
    reward=float(j<goals)
    if method=="wingless_r6_observed_route" and r6reward is not None:
     reward*=r6reward
    dev.append({"family":fam,"method":method,
       "success":j<goals,"real_total_reward":reward,
       "actual_public_step_trace":[{"a":0,"before":[0,0,0,0,0,False]}]})
 return original,dev

class F5SourceOnly(unittest.TestCase):
 def test_frozen_disjoint_unused_public_worlds(self):
  c=contract()
  self.assertEqual(len(METHODS),15)
  self.assertEqual(len(FIT),24)
  self.assertEqual(len(CHECK),4)
  self.assertEqual(len(DEV),8)
  self.assertFalse(set(FIT)&set(CHECK))
  self.assertFalse(set(FIT)&set(DEV))
  self.assertFalse(set(CHECK)&set(DEV))
  self.assertFalse(set(DEV)&set(range(63400,63408)))
  self.assertFalse(c["governance"]["scientific_accepted"])
  self.assertFalse(c["governance"]["scientific_first_use"])
 def test_equal_goals_without_lower_action_cost_must_fail(self):
  orig,dev=fixtures(8,8)
  judge=outcome(orig,dev)
  self.assertEqual(judge["result"],"NO_R6_PUBLIC_EMPIRICAL_ROUTE_EFFICIENCY_ADVANCEMENT")
  self.assertFalse(judge["criteria"]["fourrooms_reward_plus_10pct_R5"])
  self.assertFalse(judge["criteria"]["fourrooms_steps_90pct_R5"])
 def test_more_goals_but_bad_reward_is_not_positive(self):
  orig,dev=fixtures(6,8,r6reward=0.1)
  judge=outcome(orig,dev)
  self.assertFalse(judge["criteria"]["fourrooms_reward_at_least_sixfield"])
 def test_positive_can_only_be_public_development(self):
  orig,dev=fixtures(4,8,six=8,planner=8)
  # More completions + sufficiently fewer actions for R6. This fixture
  # does not prove original environment reward quality.
  for x in dev:
   if x["method"]=="wingless_r5_cost_frontier":
    x["actual_public_step_trace"]=[{"a":0,"before":[0,0,0,0,0,False]}]*3
  judge=outcome(orig,dev)
  self.assertEqual(judge["result"],"BOUNDED_R6_PUBLIC_EMPIRICAL_ROUTE_EFFICIENCY_SIGNAL_NOT_NOVELTY")
  self.assertIs(judge["scientific_accepted"],False)
if __name__=="__main__":unittest.main()
