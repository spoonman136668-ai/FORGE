"""F6 preregistered falsification; synthetic source-only, not scientific evidence."""
import unittest
from k4t_f6_original_r7_physical import FIT,CHECK,DEV,METHODS,contract,outcome,FAMILIES
def fake(r5,r7,six=8,upper=8,r7reward=1):
 base={"results":{f:{"fit_dynamics_bfs":{"successes":upper,
        "mean_real_reward":upper/8,"blocked_forward_per_100_steps":0.0}}
        for f in FAMILIES}}
 rows=[]
 for f in FAMILIES:
  for method,n in (("wingless_r4_frontier",6),
                   ("wingless_r5_cost_frontier",r5),
                   ("wingless_r6_observed_route",3),
                   ("wingless_r7_physical_frontier",r7),
                   ("sixfield_fit_model_route",six)):
   for i in range(8):
    reward=float(i<n)*(r7reward if method=="wingless_r7_physical_frontier" else 1.0)
    rows.append({"family":f,"method":method,"success":i<n,
       "real_total_reward":reward,
       "actual_public_step_trace":[{"a":0,"before":[0,0,0,0,0,0]}]})
 return base,rows
class FrozenF6(unittest.TestCase):
 def test_source_cohorts_are_new_and_frozen(self):
  c=contract()
  self.assertEqual(len(METHODS),16)
  self.assertEqual((len(FIT),len(CHECK),len(DEV)),(24,4,8))
  self.assertFalse(set(FIT)&set(CHECK))
  self.assertFalse(set(FIT)&set(DEV))
  self.assertFalse(set(CHECK)&set(DEV))
  self.assertFalse(set(DEV)&set(range(73400,73408)))
  self.assertFalse(c["governance"]["scientificFirstUse"])
 def test_heading_only_regression_must_fail(self):
  a,b=fake(8,3)
  v=outcome(a,b)
  self.assertEqual(v["result"],"NO_R7_PHYSICAL_ROUTE_ADVANCEMENT")
  self.assertFalse(v["criteria"]["fourrooms_R7_goals_at_least_R5"])
 def test_goal_only_without_mean_reward_fails(self):
  a,b=fake(8,8,r7reward=.5)
  v=outcome(a,b)
  self.assertFalse(v["criteria"]["fourrooms_R7_reward_at_least_R5"])
 def test_public_positive_never_claims_sci_acceptance(self):
  a,b=fake(8,8)
  v=outcome(a,b)
  self.assertIs(v["scientific_accepted"],False)
  self.assertEqual(v["result"],"BOUNDED_R7_PHYSICAL_ROUTE_PUBLIC_DEV_SIGNAL_NOT_NOVELTY")
if __name__=="__main__":unittest.main()
