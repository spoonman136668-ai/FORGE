"""F4 prereg thresholds and independent six-public-field control falsifiers."""
import unittest
from collections import Counter
from k4t_f4_original_r5_cost import contract,FIT,CHECK,DEV,METHODS,FAMILIES,outcome
from k4t_f4_sixfield_conventional import fit,SixFieldConventional

def results(r4=5,r5=5,six=5,pl=8):
 old={"results":{}}
 for f in FAMILIES:
  old["results"][f]={
    "fit_dynamics_bfs":{"successes":pl,"mean_real_reward":pl/8,
        "blocked_forward_per_100_steps":0.0},
    "wingless_r3":{"successes":0,"mean_real_reward":0,
        "blocked_forward_per_100_steps":0.0},
  }
 dev=[]
 for fam in FAMILIES:
  for method,n in (("wingless_r4_frontier",r4),("wingless_r5_cost_frontier",r5),
                   ("sixfield_fit_model_route",six)):
   for j in range(8):
    dev.append({"family":fam,"method":method,"success":j<n,
      "real_total_reward":float(j<n),
      "actual_public_step_trace":[{"a":0,"before":[0,0,0,0,0,False]}]})
 return old,dev

class F4FrozenTests(unittest.TestCase):
 def test_disjoint_fresh_original_cohorts(self):
  p=contract()
  self.assertEqual(len(METHODS),14)
  self.assertEqual((len(FIT),len(CHECK),len(DEV)),(24,4,8))
  self.assertFalse(set(FIT)&set(DEV))
  self.assertFalse(set(CHECK)&set(DEV))
  self.assertFalse(set(DEV)&set(range(53400,53408)))
  self.assertFalse(p["protected_scientific_first_use"])
 def test_no_relative_native_goal_gain_is_no_go(self):
  old,dev=results(r4=5,r5=5)
  judge=outcome(old,dev)
  self.assertEqual(judge["result"],"NO_R5_COST_AWARE_NAVIGATION_ADVANCEMENT")
  self.assertFalse(judge["criteria"]["fourrooms_extra_goals_over_R4"])
 def test_old_reward_threshold_still_bind(self):
  old,dev=results(r4=5,r5=6,six=4,pl=8)
  for x in dev:
   if x["method"]=="wingless_r5_cost_frontier":
    x["real_total_reward"]*=0.1
  judge=outcome(old,dev)
  self.assertFalse(judge["criteria"]["fourrooms_reward_vs_full_map_planner"])
 def test_source_only_positive_cannot_claim_sci_accepted(self):
  old,dev=results(r4=4,r5=8,six=7,pl=8)
  judge=outcome(old,dev)
  self.assertEqual(judge["result"],"BOUNDED_R5_COST_AWARE_PUBLIC_DEV_GAIN_NOT_NOVELTY")
  self.assertIs(judge["scientific_accepted"],False)
  self.assertIs(judge["full_map_control_has_extra_information"],True)
 def test_six_field_control_cannot_infer_unlearned_world(self):
  sample=[]
  for direction in range(4):
   for blocked in (False,True):
    for a in (0,1,2):
     b={"X":20,"Y":20,"GoalX":24,"GoalY":23,
       "Direction":direction,"FrontBlocked":blocked}
     nxt=dict(b)
     # Synthetic fixture, not real MiniGrid source evidence.
     if a==0:nxt["Direction"]=(direction+3)%4
     if a==1:nxt["Direction"]=(direction+1)%4
     if a==2 and not blocked:
      if direction==0:nxt["X"]+=1
      if direction==1:nxt["Y"]+=1
      if direction==2:nxt["X"]-=1
      if direction==3:nxt["Y"]-=1
     sample.extend({"before":b,"after":nxt,"action":a} for _ in range(500))
  trained,digest=fit(sample)
  self.assertEqual(len(digest),64)
  control=SixFieldConventional(trained)
  s={"X":20,"Y":20,"GoalX":23,"GoalY":22,"Direction":0,"FrontBlocked":False}
  a=control.choose(s)
  self.assertIn(a,(0,1,2))
  with self.assertRaises(ValueError):control.choose(s)
  next_state=dict(s)
  control.feedback(s,a,next_state)
  self.assertEqual(control.steps,1)
  self.assertEqual(len(trained),24)
if __name__=="__main__":unittest.main()
